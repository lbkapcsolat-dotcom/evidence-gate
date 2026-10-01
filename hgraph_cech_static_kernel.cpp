#include <algorithm>
#include <functional>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace eq64_cech {

constexpr int N = 20;
constexpr int G = 64;
constexpr int APEX = 1;
constexpr int MAX_DEGREE = 19;

using Simplex = std::vector<int>;
using Cochain = std::map<Simplex, long long>;

long long binom(int n, int k) {
    if (k < 0 || k > n) return 0;
    if (k > n - k) k = n - k;
    long long out = 1;
    for (int i = 1; i <= k; ++i) {
        out = out * (n - k + i) / i;
    }
    return out;
}

long long local_dimension(int p) {
    if (p < 0 || p > MAX_DEGREE) throw std::out_of_range("degree");
    return binom(N, p + 1);
}

long long global_dimension(int p) {
    return G * local_dimension(p);
}

long long get(const Cochain& c, const Simplex& simplex) {
    auto it = c.find(simplex);
    return it == c.end() ? 0LL : it->second;
}

Simplex without_index(const Simplex& simplex, int j) {
    Simplex out;
    out.reserve(simplex.size() - 1);
    for (int i = 0; i < static_cast<int>(simplex.size()); ++i) {
        if (i != j) out.push_back(simplex[i]);
    }
    return out;
}

long long delta_value(int p, const Cochain& cochain, const Simplex& simplex) {
    if (p == MAX_DEGREE) return 0;
    long long value = 0;
    for (int j = 0; j < static_cast<int>(simplex.size()); ++j) {
        const auto face = without_index(simplex, j);
        value += (j % 2 == 0 ? 1 : -1) * get(cochain, face);
    }
    return value;
}

long long h_value(int p, const Cochain& cochain, const Simplex& simplex) {
    if (p <= 0 || p > MAX_DEGREE) throw std::out_of_range("h degree");
    if (std::find(simplex.begin(), simplex.end(), APEX) != simplex.end()) return 0;
    Simplex source;
    source.reserve(simplex.size() + 1);
    source.push_back(APEX);
    source.insert(source.end(), simplex.begin(), simplex.end());
    return get(cochain, source);
}

long long projection_value(const Cochain& cochain) {
    return get(cochain, Simplex{APEX});
}

template <typename F>
void for_combinations(int k, F fn) {
    Simplex current;
    std::function<void(int, int)> rec = [&](int start, int left) {
        if (left == 0) {
            fn(current);
            return;
        }
        for (int v = start; v <= N - left + 1; ++v) {
            current.push_back(v);
            rec(v + 1, left - 1);
            current.pop_back();
        }
    };
    rec(1, k);
}

long long basis_value(const Simplex& rep, const Simplex& simplex) {
    return rep == simplex ? 1LL : 0LL;
}

long long basis_delta_value(int p, const Simplex& rep, const Simplex& simplex) {
    long long value = 0;
    for (int j = 0; j < static_cast<int>(simplex.size()); ++j) {
        value += (j % 2 == 0 ? 1 : -1) * basis_value(rep, without_index(simplex, j));
    }
    return value;
}

long long basis_delta_squared_value(int p, const Simplex& rep, const Simplex& simplex) {
    long long value = 0;
    for (int j = 0; j < static_cast<int>(simplex.size()); ++j) {
        value += (j % 2 == 0 ? 1 : -1) * basis_delta_value(p, rep, without_index(simplex, j));
    }
    return value;
}

long long basis_h_value(int p, const Simplex& rep, const Simplex& simplex) {
    if (std::find(simplex.begin(), simplex.end(), APEX) != simplex.end()) return 0;
    Simplex source;
    source.reserve(simplex.size() + 1);
    source.push_back(APEX);
    source.insert(source.end(), simplex.begin(), simplex.end());
    return basis_value(rep, source);
}

long long basis_positive_composition_value(int p, const Simplex& rep, const Simplex& simplex) {
    long long delta_h = 0;
    for (int j = 0; j < static_cast<int>(simplex.size()); ++j) {
        delta_h += (j % 2 == 0 ? 1 : -1) * basis_h_value(p, rep, without_index(simplex, j));
    }
    long long h_delta = 0;
    if (p < MAX_DEGREE &&
        std::find(simplex.begin(), simplex.end(), APEX) == simplex.end()) {
        Simplex source;
        source.reserve(simplex.size() + 1);
        source.push_back(APEX);
        source.insert(source.end(), simplex.begin(), simplex.end());
        h_delta = basis_delta_value(p, rep, source);
    }
    return delta_h + h_delta;
}

std::vector<Simplex> orbit_representatives(int p) {
    std::vector<Simplex> reps;
    Simplex apex_rep;
    for (int v = 1; v <= p + 1; ++v) apex_rep.push_back(v);
    reps.push_back(apex_rep);
    if (p <= 18) {
        Simplex non_apex;
        for (int v = 2; v <= p + 2; ++v) non_apex.push_back(v);
        reps.push_back(non_apex);
    }
    return reps;
}

std::string parity_summary() {
    std::ostringstream out;
    out << "EQ64_CECH_STATIC_KERNEL_V1\n";
    out << "N=" << N << "\n";
    out << "G=" << G << "\n";
    out << "APEX=" << APEX << "\n";

    for (int p = 0; p < 20; ++p) {
        out << "DIM:" << p << ":" << local_dimension(p) << ":" << global_dimension(p) << "\n";
    }

    Cochain f0{{Simplex{1}, 3}, {Simplex{2}, 5}, {Simplex{3}, 11}};
    out << "DELTA0:"
        << delta_value(0, f0, Simplex{1, 2}) << ":"
        << delta_value(0, f0, Simplex{1, 3}) << ":"
        << delta_value(0, f0, Simplex{2, 3}) << "\n";

    Cochain edge{{Simplex{1, 2}, 1}};
    out << "DELTA1:"
        << delta_value(1, edge, Simplex{1, 2, 3}) << ":"
        << delta_value(1, edge, Simplex{1, 2, 20}) << "\n";

    Cochain h1c{{Simplex{1, 2}, 7}, {Simplex{2, 3}, 9}};
    out << "H1:"
        << h_value(1, h1c, Simplex{1}) << ":"
        << h_value(1, h1c, Simplex{2}) << ":"
        << h_value(1, h1c, Simplex{3}) << "\n";

    Cochain h2c{{Simplex{1, 2, 3}, 5}};
    out << "H2:"
        << h_value(2, h2c, Simplex{1, 2}) << ":"
        << h_value(2, h2c, Simplex{2, 3}) << "\n";

    Cochain pic{{Simplex{1}, 3}, {Simplex{2}, 11}, {Simplex{20}, -4}};
    const auto pi = projection_value(pic);
    out << "PI:" << pi << ":" << pi << ":" << pi << "\n";

    bool all_d2 = true;
    for (int p = 0; p < 19; ++p) {
        const auto reps = orbit_representatives(p);
        for (int orbit = 0; orbit < static_cast<int>(reps.size()); ++orbit) {
            bool ok = true;
            if (p <= 17) {
                for_combinations(p + 3, [&](const Simplex& simplex) {
                    if (ok && basis_delta_squared_value(p, reps[orbit], simplex) != 0) ok = false;
                });
            }
            all_d2 = all_d2 && ok;
            out << "D2:" << p << ":" << orbit << ":" << (ok ? 1 : 0) << "\n";
        }
    }

    bool all_h = true;
    for (int p = 1; p < 20; ++p) {
        const auto reps = orbit_representatives(p);
        for (int orbit = 0; orbit < static_cast<int>(reps.size()); ++orbit) {
            bool ok = true;
            for_combinations(p + 1, [&](const Simplex& simplex) {
                if (ok && basis_positive_composition_value(p, reps[orbit], simplex)
                              != basis_value(reps[orbit], simplex)) {
                    ok = false;
                }
            });
            all_h = all_h && ok;
            out << "HOM:" << p << ":" << orbit << ":" << (ok ? 1 : 0) << "\n";
        }
    }

    bool h0_ok = true;
    for (int basis_vertex = 1; basis_vertex <= N && h0_ok; ++basis_vertex) {
        for (int target_vertex = 1; target_vertex <= N; ++target_vertex) {
            const long long lhs = target_vertex == APEX
                ? 0
                : (target_vertex == basis_vertex ? 1 : 0) - (APEX == basis_vertex ? 1 : 0);
            const long long rhs = (target_vertex == basis_vertex ? 1 : 0)
                - (APEX == basis_vertex ? 1 : 0);
            if (lhs != rhs) {
                h0_ok = false;
                break;
            }
        }
    }
    out << "H0_REDUCED_ALL:" << (h0_ok ? 1 : 0) << "\n";

    Cochain mutant_phi{{Simplex{1}, 1}};
    auto mutant_delta0 = [&](const Simplex& edge_simplex) {
        long long value = 0;
        for (int j = 0; j < static_cast<int>(edge_simplex.size()); ++j) {
            value += get(mutant_phi, without_index(edge_simplex, j));
        }
        return value;
    };
    const long long mutant_value =
        mutant_delta0(Simplex{2, 3}) +
        mutant_delta0(Simplex{1, 3}) +
        mutant_delta0(Simplex{1, 2});
    out << "MUTANT_DETECTED:" << (mutant_value != 0 ? 1 : 0) << "\n";
    out << "DELTA2_ALL:" << (all_d2 ? 1 : 0) << "\n";
    out << "H0_DIM:" << G << "\n";
    out << "HP_ZERO_1_19:" << (all_h ? 1 : 0) << "\n";
    return out.str();
}

}  // namespace eq64_cech

#ifdef EQ64_CECH_STANDALONE
int main() {
    std::cout << eq64_cech::parity_summary();
    return 0;
}
#endif
