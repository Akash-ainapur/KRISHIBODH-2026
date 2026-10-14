#include <random>

#include "check.hpp"
#include "krishi/protocol.hpp"

using namespace krishi;

TEST(crc16_known_check_value) {
    // The standard check value for CRC-16/CCITT-FALSE over ASCII "123456789" is 0x29B1.
    const std::uint8_t msg[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    CHECK_EQ(proto::crc16(msg, 9), std::uint16_t{0x29B1});
    CHECK_EQ(crc16_table(msg, 9), std::uint16_t{0x29B1});
}

TEST(cobs_output_never_contains_zero) {
    std::mt19937 rng(3);
    std::uniform_int_distribution<int> byte(0, 3);  // lots of zeros
    for (int trial = 0; trial < 200; ++trial) {
        std::vector<std::uint8_t> in(static_cast<std::size_t>(trial % 300));
        for (auto& b : in) b = static_cast<std::uint8_t>(byte(rng));
        std::vector<std::uint8_t> enc(in.size() + in.size() / 254 + 2), dec(in.size() + 1);
        const std::size_t n = proto::cobs_encode(in.data(), in.size(), enc.data());
        for (std::size_t i = 0; i < n; ++i) CHECK(enc[i] != 0);
        const int m = proto::cobs_decode(enc.data(), n, dec.data());
        CHECK_EQ(m, static_cast<int>(in.size()));
        dec.resize(in.size());
        CHECK(dec == in);
    }
}

TEST(frame_round_trip) {
    const proto::Frame f = make_move(42, proto::SMART_WATER, {2000, 800, 10000});
    const auto frames = decode_all(encode(f));
    CHECK_EQ(frames.size(), std::size_t{1});
    CHECK_EQ(frames[0].seq, std::uint8_t{42});
    CHECK_EQ(frames[0].cmd, std::uint8_t{proto::SMART_WATER});
    CHECK_EQ(proto::get_i32(frames[0].payload + 4), 800);
}

TEST(negative_coordinates_survive) {
    const proto::Frame f = make_move(1, proto::MOVE, {-1, -2000000, 0});
    const auto got = decode_all(encode(f));
    CHECK_EQ(proto::get_i32(got[0].payload), -1);
    CHECK_EQ(proto::get_i32(got[0].payload + 4), -2000000);
}

TEST(every_single_bit_flip_is_detected) {
    const auto wire = encode(make_move(7, proto::MOVE, {3000, 1500, 10000}));
    std::size_t detected = 0, total = 0;
    for (std::size_t byte = 0; byte + 1 < wire.size(); ++byte) {  // last byte is the delimiter
        for (int bit = 0; bit < 8; ++bit) {
            auto bad = wire;
            bad[byte] ^= static_cast<std::uint8_t>(1U << bit);
            std::size_t errors = 0;
            const auto frames = decode_all(bad, &errors);
            ++total;
            // A flip can also create a 0x00, splitting the frame in two: still rejected, never accepted.
            if (frames.empty()) ++detected;
        }
    }
    CHECK_EQ(detected, total);
}

TEST(decoder_resyncs_after_garbage) {
    std::vector<std::uint8_t> stream = {0x13, 0x37, 0xFF, 0x00};  // noise, then a delimiter
    const auto good = encode(make_move(9, proto::MOVE, {1, 2, 3}));
    stream.insert(stream.end(), good.begin(), good.end());
    std::size_t bad = 0;
    const auto frames = decode_all(stream, &bad);
    CHECK_EQ(frames.size(), std::size_t{1});
    CHECK_EQ(bad, std::size_t{1});
    CHECK_EQ(frames[0].seq, std::uint8_t{9});
}

TEST(rejects_oversized_payload) {
    proto::Frame f{};
    f.len = static_cast<std::uint8_t>(proto::kMaxPayload + 1);
    CHECK_THROWS(encode(f));
}
