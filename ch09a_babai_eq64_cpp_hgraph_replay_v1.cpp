#include <hgraph/lib/std/standard_types.h>
#include <hgraph/lib/testing/eval_node.h>
#include <hgraph/types/graph_wiring.h>
#include <hgraph/types/operator_dispatch.h>
#include <hgraph/types/static_node.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace ch09a {

using Rotation = std::array<int, 6>;

int permutation_parity(const std::array<int, 3>& p)
{
    int inversions = 0;
    for (int i = 0; i < 3; ++i)
        for (int j = i + 1; j < 3; ++j)
            if (p[i] > p[j]) ++inversions;
    return (inversions % 2 == 0) ? 1 : -1;
}

std::vector<Rotation> build_rotations()
{
    std::vector<Rotation> out;
    std::array<int, 3> perm{0, 1, 2};
    do
    {
        const int parity = permutation_parity(perm);
        for (int sx : {-1, 1})
        for (int sy : {-1, 1})
        for (int sz : {-1, 1})
        {
            const std::array<int, 3> signs{sx, sy, sz};
            if (parity * sx * sy * sz != 1) continue;

            Rotation r{};
            for (int face = 0; face < 6; ++face)
            {
                const int axis = face / 2;
                const int face_sign = (face % 2 == 0) ? 1 : -1;
                const int out_axis = perm[axis];
                const int out_sign = face_sign * signs[axis];
                r[face] = 2 * out_axis + (out_sign == 1 ? 0 : 1);
            }
            out.push_back(r);
        }
    }
    while (std::next_permutation(perm.begin(), perm.end()));

    std::set<Rotation> unique(out.begin(), out.end());
    if (out.size() != 24 || unique.size() != 24)
        throw std::runtime_error("rotation set must contain exactly 24 unique proper cube rotations");
    return out;
}

const std::vector<Rotation>& rotations()
{
    static const std::vector<Rotation> value = build_rotations();
    return value;
}

bool coordinate_bit(std::uint8_t state, int coordinate)
{
    return ((state >> (5 - coordinate)) & 1U) != 0U;
}

std::uint8_t set_coordinate_bit(std::uint8_t state, int coordinate)
{
    return static_cast<std::uint8_t>(state | (1U << (5 - coordinate)));
}

std::uint8_t apply_rotation(std::uint8_t state, const Rotation& r)
{
    std::uint8_t out = 0;
    for (int coordinate = 0; coordinate < 6; ++coordinate)
    {
        if (coordinate_bit(state, coordinate))
            out = set_coordinate_bit(out, r[coordinate]);
    }
    return out;
}

struct Record
{
    int x;
    int canonical;
    int orbit_size;
    int stabilizer_size;
};

Record record_for(int raw)
{
    if (raw < 0 || raw > 63) throw std::out_of_range("state must be in [0,63]");
    const auto x = static_cast<std::uint8_t>(raw);

    std::set<int> orbit;
    int stabilizer = 0;
    for (const auto& r : rotations())
    {
        const int y = static_cast<int>(apply_rotation(x, r));
        orbit.insert(y);
        if (y == raw) ++stabilizer;
    }

    if (orbit.empty()) throw std::runtime_error("empty orbit");
    const int orbit_size = static_cast<int>(orbit.size());
    if (orbit_size * stabilizer != 24)
        throw std::runtime_error("orbit-stabilizer violation");

    return Record{raw, *orbit.begin(), orbit_size, stabilizer};
}

std::string record_json(int raw)
{
    const auto r = record_for(raw);
    std::ostringstream out;
    out << "{\"x\":" << r.x
        << ",\"canonical\":" << r.canonical
        << ",\"orbit_size\":" << r.orbit_size
        << ",\"stabilizer_size\":" << r.stabilizer_size
        << "}";
    return out.str();
}

std::string orbit_profile()
{
    std::set<int> seen;
    std::vector<int> sizes;
    for (int x = 0; x < 64; ++x)
    {
        if (seen.count(x)) continue;
        std::set<int> orbit;
        for (const auto& r : rotations())
            orbit.insert(static_cast<int>(apply_rotation(static_cast<std::uint8_t>(x), r)));
        seen.insert(orbit.begin(), orbit.end());
        sizes.push_back(static_cast<int>(orbit.size()));
    }
    std::sort(sizes.begin(), sizes.end());
    std::ostringstream out;
    for (std::size_t i = 0; i < sizes.size(); ++i)
    {
        if (i) out << ",";
        out << sizes[i];
    }
    return out.str();
}

int canonical_label_count()
{
    std::set<int> labels;
    for (int x = 0; x < 64; ++x)
        labels.insert(record_for(x).canonical);
    return static_cast<int>(labels.size());
}

} // namespace ch09a

namespace ch09a_hgraph {

using namespace hgraph;

struct babai_eq64_canonical_record
    : Operator<"equilibrium.babai_eq64.canonical_record",
               In<"state", TS<Int>>,
               Out<TS<Str>>>
{
};

struct babai_eq64_canonical_record_cpp
{
    static constexpr auto name = "babai_eq64_canonical_record_cpp";

    static void eval(In<"state", TS<Int>> state, Out<TS<Str>> out)
    {
        const auto raw = static_cast<std::int64_t>(state.value());
        if (raw < 0 || raw > 63)
            throw std::out_of_range("state must be in [0,63]");
        out.set(Str{ch09a::record_json(static_cast<int>(raw))});
    }
};

struct babai_eq64_replay_graph
{
    static constexpr auto name = "babai_eq64_replay_graph";

    static Port<TS<Str>> compose(Wiring& w, Port<TS<Int>> state)
    {
        return wire<babai_eq64_canonical_record, TS<Str>>(w, state);
    }
};

} // namespace ch09a_hgraph

int main()
{
    using namespace hgraph;
    using namespace ch09a_hgraph;

    (void)stdlib::register_standard_types();
    register_overload<babai_eq64_canonical_record,
                      babai_eq64_canonical_record_cpp>();

    if (ch09a::rotations().size() != 24)
    {
        std::cerr << "ROTATION_COUNT_FAIL\n";
        return EXIT_FAILURE;
    }

    const std::string profile = ch09a::orbit_profile();
    if (profile != "1,1,3,3,6,6,8,12,12,12")
    {
        std::cerr << "ORBIT_PROFILE_FAIL=" << profile << "\n";
        return EXIT_FAILURE;
    }

    const int canonical_count = ch09a::canonical_label_count();
    if (canonical_count != 10)
    {
        std::cerr << "CANONICAL_LABEL_COUNT_FAIL=" << canonical_count << "\n";
        return EXIT_FAILURE;
    }

    std::size_t pass = 0;
    for (int raw = 0; raw < 64; ++raw)
    {
        const auto standalone = ch09a::record_json(raw);
        const auto out = testing::eval_node<babai_eq64_replay_graph>(
            std::vector<std::optional<Int>>{static_cast<Int>(raw)});

        if (out.size() != 1 || !out.front().has_value())
        {
            std::cerr << "STATE_" << raw << "_HGRAPH_NO_OUTPUT\n";
            return EXIT_FAILURE;
        }

        const std::string observed = out.front().value();
        const bool equal = observed == standalone;
        const auto rec = ch09a::record_for(raw);

        std::cout
            << "{\"x\":" << rec.x
            << ",\"canonical\":" << rec.canonical
            << ",\"orbit_size\":" << rec.orbit_size
            << ",\"stabilizer_size\":" << rec.stabilizer_size
            << ",\"hgraph_equal\":" << (equal ? "true" : "false")
            << "}\n";

        if (!equal)
        {
            std::cerr << "STATE_" << raw << "_CPP_HGRAPH_REPLAY_MISMATCH\n";
            return EXIT_FAILURE;
        }
        ++pass;
    }

    std::cout << "ROTATIONS=24\n";
    std::cout << "CANONICAL_LABELS=10\n";
    std::cout << "ORBIT_PROFILE=" << profile << "\n";
    std::cout << "ORBIT_STABILIZER=64/64\n";
    std::cout << "CPP_HGRAPH_EQ64_MATRIX=" << pass << "/64\n";
    return pass == 64 ? EXIT_SUCCESS : EXIT_FAILURE;
}
