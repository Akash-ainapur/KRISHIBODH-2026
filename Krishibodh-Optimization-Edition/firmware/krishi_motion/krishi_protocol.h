#pragma once
// KRISHIBODH binary wire protocol. Compiled by BOTH the Arduino and the PC.
//
// Today the PC sends text like "SMART:2000,800,10000\n". Problems:
//   - a flipped bit on the wire silently becomes a different coordinate
//   - no way to tell which command a reply belongs to
//   - "Ready for next command" is parsed out of free text
//
// A frame on the wire:
//   COBS( seq | cmd | len | payload[len] | crc_hi | crc_lo )  0x00
//
//   seq   1 byte, increments per command; replies echo it (match ACK to command)
//   cmd   1 byte, see Cmd
//   len   1 byte, payload length (max kMaxPayload)
//   crc   CRC-16/CCITT-FALSE over seq..payload; any corruption fails the check
//   COBS  "Consistent Overhead Byte Stuffing": rewrites the frame so it contains
//         no 0x00 bytes, which makes 0x00 a safe end-of-frame marker. If bytes
//         are lost, the receiver resynchronises at the next 0x00.
//
// Rules: no STL, no heap, fixed buffers. Works with avr-gcc.

#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace krishi {
namespace proto {

enum Cmd : uint8_t {
    MOVE = 0x01,          // payload: x, y, z as int32 little-endian (12 bytes)
    SMART_WATER = 0x02,   // move, read moisture, water only if dry
    FORCE_WATER = 0x03,   // move and water unconditionally
    MOISTURE_GET = 0x04,  // no payload; reply MOISTURE
    HOME = 0x05,          // no payload
    STOP = 0x06,          // no payload; abort current motion
    ACK = 0x80,           // command accepted (echoes seq)
    NACK = 0x81,          // command rejected; payload[0] = reason
    MOISTURE = 0x82,      // payload: uint16 reading
    DONE = 0x83,          // command finished; payload[0] = 1 if it watered
};

enum NackReason : uint8_t { BAD_LENGTH = 1, QUEUE_FULL = 2, UNKNOWN_CMD = 3 };

const size_t kMaxPayload = 16;
const size_t kMaxRaw = 3 + kMaxPayload + 2;          // seq, cmd, len, payload, crc
const size_t kMaxEncoded = kMaxRaw + kMaxRaw / 254 + 2;  // COBS overhead + 0x00 delimiter

struct Frame {
    uint8_t seq;
    uint8_t cmd;
    uint8_t len;
    uint8_t payload[kMaxPayload];
};

// CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF. Bit-by-bit: tiny code, no table.
// (The PC side also has a 256-entry table version, 2.5x faster in bench/, too big for AVR RAM.)
inline uint16_t crc16(const uint8_t* data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; ++i) {
        // Widen to uint16_t BEFORE shifting: on AVR `int` is 16-bit, so data[i] << 8
        // as a signed int overflows for bytes >= 128 (undefined behaviour). PCs hide this.
        crc ^= static_cast<uint16_t>(static_cast<uint16_t>(data[i]) << 8);
        for (int bit = 0; bit < 8; ++bit)
            crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021) : static_cast<uint16_t>(crc << 1);
    }
    return crc;
}

// COBS encode. `out` must hold len + len/254 + 1 bytes. Returns bytes written
// (no trailing 0x00; the caller appends the delimiter).
inline size_t cobs_encode(const uint8_t* in, size_t len, uint8_t* out) {
    size_t write = 1, code_at = 0;
    uint8_t code = 1;
    for (size_t i = 0; i < len; ++i) {
        if (in[i] == 0) {               // a zero ends the current block
            out[code_at] = code;
            code_at = write++;
            code = 1;
        } else {
            out[write++] = in[i];
            if (++code == 0xFF) {       // block full (254 data bytes)
                out[code_at] = code;
                code_at = write++;
                code = 1;
            }
        }
    }
    out[code_at] = code;
    return write;
}

// COBS decode. Returns decoded length, or -1 if the input is malformed.
inline int cobs_decode(const uint8_t* in, size_t len, uint8_t* out) {
    size_t read = 0, write = 0;
    while (read < len) {
        const uint8_t code = in[read++];
        if (code == 0 || read + code - 1 > len) return -1;
        for (uint8_t k = 1; k < code; ++k) out[write++] = in[read++];
        if (code != 0xFF && read < len) out[write++] = 0;
    }
    return static_cast<int>(write);
}

// Builds a complete wire frame (COBS + trailing 0x00) into `out`
// (at least kMaxEncoded bytes). Returns bytes to send, or 0 if len is too big.
inline size_t encode_frame(const Frame& f, uint8_t* out) {
    if (f.len > kMaxPayload) return 0;
    uint8_t raw[kMaxRaw];
    raw[0] = f.seq;
    raw[1] = f.cmd;
    raw[2] = f.len;
    memcpy(raw + 3, f.payload, f.len);
    const uint16_t crc = crc16(raw, 3u + f.len);
    raw[3 + f.len] = static_cast<uint8_t>(crc >> 8);
    raw[4 + f.len] = static_cast<uint8_t>(crc & 0xFF);
    const size_t n = cobs_encode(raw, 5u + f.len, out);
    out[n] = 0x00;
    return n + 1;
}

// Byte-at-a-time receiver: call feed() for every byte from the serial port.
// It never blocks, so the firmware can keep stepping motors while bytes arrive.
class FrameDecoder {
public:
    enum Result : uint8_t { NEED_MORE, GOT_FRAME, BAD_FRAME };

    Result feed(uint8_t byte, Frame& out) {
        if (byte != 0x00) {
            if (n_ < sizeof(buf_)) buf_[n_++] = byte;
            else overflow_ = true;          // keep discarding until the next delimiter
            return NEED_MORE;
        }
        const size_t n = n_;
        const bool overflow = overflow_;
        n_ = 0;
        overflow_ = false;
        if (n == 0) return NEED_MORE;       // empty frame / leading delimiter
        if (overflow) return BAD_FRAME;

        uint8_t raw[kMaxEncoded];
        const int len = cobs_decode(buf_, n, raw);
        if (len < 5) return BAD_FRAME;
        const size_t body = static_cast<size_t>(len) - 2;
        const uint16_t got = static_cast<uint16_t>(static_cast<uint16_t>(raw[body]) << 8 | raw[body + 1]);
        if (crc16(raw, body) != got) return BAD_FRAME;
        if (raw[2] > kMaxPayload || static_cast<size_t>(raw[2]) + 3 != body) return BAD_FRAME;

        out.seq = raw[0];
        out.cmd = raw[1];
        out.len = raw[2];
        memcpy(out.payload, raw + 3, out.len);
        return GOT_FRAME;
    }

private:
    uint8_t buf_[kMaxEncoded];
    size_t n_ = 0;
    bool overflow_ = false;
};

// Little-endian int32 helpers (explicit byte order: never memcpy a struct across machines).
inline void put_i32(uint8_t* p, int32_t v) {
    const uint32_t u = static_cast<uint32_t>(v);
    p[0] = static_cast<uint8_t>(u);
    p[1] = static_cast<uint8_t>(u >> 8);
    p[2] = static_cast<uint8_t>(u >> 16);
    p[3] = static_cast<uint8_t>(u >> 24);
}
inline int32_t get_i32(const uint8_t* p) {
    return static_cast<int32_t>(static_cast<uint32_t>(p[0]) | static_cast<uint32_t>(p[1]) << 8 |
                                static_cast<uint32_t>(p[2]) << 16 | static_cast<uint32_t>(p[3]) << 24);
}

}  // namespace proto
}  // namespace krishi
