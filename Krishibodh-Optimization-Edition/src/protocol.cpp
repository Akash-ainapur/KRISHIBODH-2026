#include "krishi/protocol.hpp"

#include <array>
#include <stdexcept>

namespace krishi {

namespace {
// Built once at compile time (constexpr), so there is no start-up cost.
constexpr std::array<std::uint16_t, 256> make_crc_table() {
    std::array<std::uint16_t, 256> t{};
    for (std::uint32_t i = 0; i < 256; ++i) {
        std::uint32_t crc = i << 8;
        for (int bit = 0; bit < 8; ++bit) crc = (crc & 0x8000U) ? (crc << 1) ^ 0x1021U : crc << 1;
        t[i] = static_cast<std::uint16_t>(crc & 0xFFFFU);
    }
    return t;
}
constexpr auto kCrcTable = make_crc_table();
}  // namespace

std::uint16_t crc16_table(const std::uint8_t* data, std::size_t len) {
    std::uint16_t crc = 0xFFFF;
    for (std::size_t i = 0; i < len; ++i)
        crc = static_cast<std::uint16_t>((crc << 8) ^ kCrcTable[((crc >> 8) ^ data[i]) & 0xFFU]);
    return crc;
}

std::vector<std::uint8_t> encode(const proto::Frame& f) {
    std::vector<std::uint8_t> out(proto::kMaxEncoded);
    const std::size_t n = proto::encode_frame(f, out.data());
    if (n == 0) throw std::invalid_argument("payload too long");
    out.resize(n);
    return out;
}

proto::Frame make_move(std::uint8_t seq, proto::Cmd cmd, const Point& p) {
    proto::Frame f{};
    f.seq = seq;
    f.cmd = cmd;
    f.len = 12;
    proto::put_i32(f.payload + 0, static_cast<std::int32_t>(p.x));
    proto::put_i32(f.payload + 4, static_cast<std::int32_t>(p.y));
    proto::put_i32(f.payload + 8, static_cast<std::int32_t>(p.z));
    return f;
}

std::vector<proto::Frame> decode_all(const std::vector<std::uint8_t>& bytes, std::size_t* bad) {
    std::vector<proto::Frame> frames;
    proto::FrameDecoder dec;
    proto::Frame f{};
    std::size_t errors = 0;
    for (std::uint8_t b : bytes) {
        switch (dec.feed(b, f)) {
            case proto::FrameDecoder::GOT_FRAME: frames.push_back(f); break;
            case proto::FrameDecoder::BAD_FRAME: ++errors; break;
            case proto::FrameDecoder::NEED_MORE: break;
        }
    }
    if (bad) *bad = errors;
    return frames;
}

}  // namespace krishi
