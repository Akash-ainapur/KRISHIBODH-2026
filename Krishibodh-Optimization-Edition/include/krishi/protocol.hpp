#pragma once
// PC-side conveniences around the shared wire protocol (krishi_protocol.h).

#include <cstdint>
#include <vector>

#include "krishi/geometry.hpp"
#include "krishi_protocol.h"

namespace krishi {

// Same CRC as proto::crc16, using a 256-entry lookup table: one table read per
// byte instead of 8 shift/xor steps. Fine on a PC; 512 bytes is a quarter of
// an Arduino Uno's RAM, which is why the firmware uses the bitwise version.
std::uint16_t crc16_table(const std::uint8_t* data, std::size_t len);

std::vector<std::uint8_t> encode(const proto::Frame& f);
proto::Frame make_move(std::uint8_t seq, proto::Cmd cmd, const Point& p);
// Decodes every complete frame in a byte stream; counts frames that failed CRC/COBS.
std::vector<proto::Frame> decode_all(const std::vector<std::uint8_t>& bytes, std::size_t* bad = nullptr);

}  // namespace krishi
