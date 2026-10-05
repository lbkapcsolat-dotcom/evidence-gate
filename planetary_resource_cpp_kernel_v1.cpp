#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <iostream>
#include <map>
#include <numeric>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace eqprs {

struct Fraction {
    std::int64_t n{0};
    std::int64_t d{1};

    Fraction() = default;
    Fraction(std::int64_t num) : n(num), d(1) {}
    Fraction(std::int64_t num, std::int64_t den) : n(num), d(den) {
        if (den == 0) throw std::invalid_argument("zero denominator");
        if (d < 0) { n = -n; d = -d; }
        const auto g = std::gcd(n < 0 ? -n : n, d);
        if (g != 0) { n /= g; d /= g; }
    }

    friend Fraction operator+(const Fraction& a, const Fraction& b) {
        return Fraction(a.n * b.d + b.n * a.d, a.d * b.d);
    }
    friend Fraction operator-(const Fraction& a, const Fraction& b) {
        return Fraction(a.n * b.d - b.n * a.d, a.d * b.d);
    }
    friend Fraction operator*(const Fraction& a, const Fraction& b) {
        return Fraction(a.n * b.n, a.d * b.d);
    }
    friend Fraction operator/(const Fraction& a, const Fraction& b) {
        if (b.n == 0) throw std::invalid_argument("division by zero");
        return Fraction(a.n * b.d, a.d * b.n);
    }
    friend bool operator==(const Fraction& a, const Fraction& b) {
        return a.n == b.n && a.d == b.d;
    }
    friend bool operator!=(const Fraction& a, const Fraction& b) { return !(a == b); }
    friend bool operator<(const Fraction& a, const Fraction& b) {
        return static_cast<__int128>(a.n) * b.d < static_cast<__int128>(b.n) * a.d;
    }
    friend bool operator>(const Fraction& a, const Fraction& b) { return b < a; }
    friend bool operator<=(const Fraction& a, const Fraction& b) { return !(b < a); }
    friend bool operator>=(const Fraction& a, const Fraction& b) { return !(a < b); }

    std::string str() const {
        if (d == 1) return std::to_string(n);
        return std::to_string(n) + "/" + std::to_string(d);
    }
};

enum class Layer { Electricity, NaturalGas, CrudeOil, Freshwater };
enum class Kind { Rate, Stock, Dimensionless };
enum class Status { Observed, Derived, Imputed, Stale, Missing, Conflicted, OutOfScope };
enum class Space { Physical, Audit, Evidence, Stress };
enum class GuardPolicy { Strict, AllowImputedWithFlag, AllowStaleWithMaxAge };

static std::string layer_name(Layer l) {
    switch (l) {
        case Layer::Electricity: return "ELECTRICITY";
        case Layer::NaturalGas: return "NATURAL_GAS";
        case Layer::CrudeOil: return "CRUDE_OIL";
        case Layer::Freshwater: return "FRESHWATER";
    }
    return "UNKNOWN";
}

struct HoldError : std::runtime_error {
    std::string code;
    explicit HoldError(std::string c) : std::runtime_error(c), code(std::move(c)) {}
};

[[noreturn]] static void hold(const std::string& code) { throw HoldError(code); }

struct QValue {
    std::optional<Fraction> value;
    Layer layer{Layer::Electricity};
    Kind kind{Kind::Rate};
    std::string interval{"T0"};
    Status status{Status::Observed};
    Space space{Space::Physical};
    std::string gas_basis{};
    std::vector<std::string> transform_chain{};
};

static QValue qv(
    std::optional<Fraction> v,
    Layer layer,
    Kind kind = Kind::Rate,
    std::string interval = "T0",
    Status status = Status::Observed,
    Space space = Space::Physical,
    std::string gas_basis = {}
) {
    QValue out;
    out.value = v;
    out.layer = layer;
    out.kind = kind;
    out.interval = std::move(interval);
    out.status = status;
    out.space = space;
    out.gas_basis = std::move(gas_basis);
    return out;
}

static const QValue& qualified_value_guard(const QValue& v, GuardPolicy policy = GuardPolicy::Strict) {
    if (v.status == Status::Conflicted) hold("HOLD_CONFLICTED_INPUT");
    if (v.status == Status::Missing) hold("HOLD_MISSING_INPUT");
    if (v.status == Status::OutOfScope) hold("HOLD_OUT_OF_SCOPE_INPUT");
    if (v.status == Status::Stale && policy != GuardPolicy::AllowStaleWithMaxAge) hold("HOLD_STALE_INPUT");
    if (policy == GuardPolicy::AllowImputedWithFlag && v.status == Status::Derived) {
        for (const auto& s : v.transform_chain) {
            if (s.rfind("imputation:", 0) == 0) hold("HOLD_IMPUTED_FLAG_ERASED");
        }
    }
    return v;
}

struct Node {
    std::string id;
    Layer layer;
    std::string node_class;
    std::string manifest_version{"V1"};
};

struct InternalEdge {
    std::string id;
    Layer layer;
    std::string source;
    std::string target;
    std::string loss_model_ref{};
};

struct BoundaryEdge {
    std::string id;
    Layer layer;
    std::string local_node;
    std::string direction;  // IMPORT / EXPORT
};

struct Storage {
    std::string id;
    Layer layer;
    std::string host_node;
    Fraction capacity;
    Fraction max_charge;
    Fraction max_discharge;
    Fraction eta_charge;
    Fraction eta_discharge;
};

struct ProcessCoefficient {
    Layer layer;
    std::string node_id;
    Fraction coefficient;
    std::string evidence_ref;
};

struct Process {
    std::string id;
    std::string process_class;
    std::vector<ProcessCoefficient> coefficients;
    std::string source_ref;
    std::string method_ref;
};

using Matrix = std::vector<std::vector<int>>;
using NodeMap = std::map<std::string, Fraction>;

static std::vector<Node> nodes_for(Layer l, std::vector<std::string> ids, std::string version = "V1") {
    const std::string cls =
        l == Layer::Electricity ? "ELECTRICITY_ZONE" :
        l == Layer::NaturalGas ? "GAS_ZONE" :
        l == Layer::CrudeOil ? "OIL_ZONE_OR_HUB" :
        "WATER_BASIN_OR_ACCOUNTING_UNIT";
    std::vector<Node> out;
    for (auto& id : ids) out.push_back(Node{std::move(id), l, cls, version});
    return out;
}

static Matrix build_internal_incidence(const std::vector<Node>& nodes, const std::vector<InternalEdge>& edges) {
    Matrix B(nodes.size(), std::vector<int>(edges.size(), 0));
    std::map<std::string, std::size_t> idx;
    for (std::size_t i = 0; i < nodes.size(); ++i) idx[nodes[i].id] = i;
    for (std::size_t j = 0; j < edges.size(); ++j) {
        if (!idx.count(edges[j].source) || !idx.count(edges[j].target)) hold("HOLD_MANIFEST_MISMATCH");
        B[idx[edges[j].source]][j] = -1;
        B[idx[edges[j].target]][j] = +1;
    }
    return B;
}

static void validate_internal_incidence(
    const Matrix& B,
    const std::vector<Node>& nodes,
    const std::vector<InternalEdge>& edges
) {
    if (B.size() != nodes.size()) hold("HOLD_MANIFEST_MISMATCH");
    for (const auto& row : B) if (row.size() != edges.size()) hold("HOLD_MANIFEST_MISMATCH");
    const auto expected = build_internal_incidence(nodes, edges);
    if (B != expected) hold("HOLD_MANIFEST_MISMATCH");
    for (std::size_t j = 0; j < edges.size(); ++j) {
        int sum = 0;
        for (const auto& row : B) sum += row[j];
        if (sum != 0) hold("HOLD_MANIFEST_MISMATCH");
    }
}

static void validate_physical_rate(const QValue& v, Layer layer, const std::string& interval) {
    qualified_value_guard(v);
    if (v.layer != layer || v.kind != Kind::Rate) hold("HOLD_UNIT_MISMATCH");
    if (v.interval != interval) hold("HOLD_TIME_BASIS_MISMATCH");
    if (v.space == Space::Audit || v.space == Space::Evidence) hold("HOLD_AUDIT_PHYSICAL_MIX");
    if (v.space == Space::Stress) hold("HOLD_STRESS_PHYSICAL_MIX");
    if (!v.value.has_value()) hold("HOLD_MISSING_INPUT");
}

struct BalanceInput {
    Layer layer;
    std::string interval{"T0"};
    std::vector<Node> nodes;
    std::vector<InternalEdge> internal_edges;
    Matrix B;
    std::vector<QValue> production;
    std::vector<QValue> demand;
    std::vector<QValue> loss;
    std::vector<QValue> internal_flow;
    std::vector<BoundaryEdge> boundary_edges{};
    std::vector<QValue> boundary_flow{};
    NodeMap storage_net{};
    NodeMap process_contribution{};
};

static NodeMap resource_balance_residual(const BalanceInput& in) {
    for (const auto& n : in.nodes) {
        if (n.layer != in.layer) hold("HOLD_MANIFEST_MISMATCH");
        if (n.manifest_version != "V1") hold("HOLD_TOPOLOGY_CHANGED");
    }
    validate_internal_incidence(in.B, in.nodes, in.internal_edges);

    if (in.production.size() != in.nodes.size() ||
        in.demand.size() != in.nodes.size() ||
        in.loss.size() != in.nodes.size() ||
        in.internal_flow.size() != in.internal_edges.size() ||
        in.boundary_flow.size() != in.boundary_edges.size()) {
        hold("HOLD_MANIFEST_MISMATCH");
    }

    bool explicit_loss = false;
    for (const auto& x : in.loss) {
        validate_physical_rate(x, in.layer, in.interval);
        if (x.value.value() != Fraction(0)) explicit_loss = true;
    }
    bool edge_loss_model = false;
    for (const auto& e : in.internal_edges) {
        if (e.layer != in.layer) hold("HOLD_MANIFEST_MISMATCH");
        if (!e.loss_model_ref.empty()) edge_loss_model = true;
    }
    if (explicit_loss && edge_loss_model) hold("HOLD_DOUBLE_COUNT_LOSS");

    std::string gas_basis;
    auto inspect_basis = [&](const QValue& v) {
        if (in.layer != Layer::NaturalGas || v.gas_basis.empty()) return;
        if (gas_basis.empty()) gas_basis = v.gas_basis;
        else if (gas_basis != v.gas_basis) hold("HOLD_HHV_LHV_BASIS_MISMATCH");
    };

    for (const auto& v : in.production) { validate_physical_rate(v, in.layer, in.interval); inspect_basis(v); }
    for (const auto& v : in.demand) { validate_physical_rate(v, in.layer, in.interval); inspect_basis(v); }
    for (const auto& v : in.internal_flow) { validate_physical_rate(v, in.layer, in.interval); inspect_basis(v); }

    std::map<std::string, std::size_t> idx;
    for (std::size_t i = 0; i < in.nodes.size(); ++i) idx[in.nodes[i].id] = i;

    NodeMap boundary_net;
    for (std::size_t i = 0; i < in.boundary_edges.size(); ++i) {
        const auto& e = in.boundary_edges[i];
        const auto& v = in.boundary_flow[i];
        if (e.layer != in.layer || !idx.count(e.local_node)) hold("HOLD_MANIFEST_MISMATCH");
        validate_physical_rate(v, in.layer, in.interval);
        if (v.value.value() < Fraction(0)) hold("HOLD_NEGATIVE_DIRECTED_FLOW");
        if (e.direction == "IMPORT") boundary_net[e.local_node] = boundary_net[e.local_node] + v.value.value();
        else if (e.direction == "EXPORT") boundary_net[e.local_node] = boundary_net[e.local_node] - v.value.value();
        else hold("HOLD_BOUNDARY_DIRECTION");
    }

    NodeMap result;
    for (std::size_t i = 0; i < in.nodes.size(); ++i) {
        Fraction transport(0);
        for (std::size_t j = 0; j < in.internal_edges.size(); ++j) {
            transport = transport + Fraction(in.B[i][j]) * in.internal_flow[j].value.value();
        }
        const auto& id = in.nodes[i].id;
        result[id] =
            in.production[i].value.value()
            - in.demand[i].value.value()
            - in.loss[i].value.value()
            + transport
            + boundary_net[id]
            + (in.storage_net.count(id) ? in.storage_net.at(id) : Fraction(0))
            + (in.process_contribution.count(id) ? in.process_contribution.at(id) : Fraction(0));
    }
    return result;
}

static NodeMap process_coupling(
    const Process& process,
    Fraction activity,
    const std::vector<Node>& nodes,
    Layer target_layer
) {
    if (process.process_class == "CORRELATION") hold("HOLD_CAUSALITY");
    if (process.source_ref.empty() || process.method_ref.empty()) hold("HOLD_PROCESS_EVIDENCE");
    std::set<std::string> node_ids;
    for (const auto& n : nodes) {
        if (n.layer != target_layer) hold("HOLD_PROCESS_SCOPE");
        node_ids.insert(n.id);
    }
    NodeMap out;
    for (const auto& n : nodes) out[n.id] = Fraction(0);
    for (const auto& c : process.coefficients) {
        if (c.layer != target_layer) continue;
        if (!node_ids.count(c.node_id)) hold("HOLD_PROCESS_SCOPE");
        if (c.evidence_ref.empty()) hold("HOLD_PROCESS_EVIDENCE");
        out[c.node_id] = out[c.node_id] + c.coefficient * activity;
    }
    return out;
}

static Fraction storage_transition(
    const Storage& s,
    Fraction stock,
    Fraction charge,
    Fraction discharge,
    Fraction delta_t = Fraction(1),
    Fraction self_loss = Fraction(0)
) {
    if (!(s.eta_charge > Fraction(0) && s.eta_charge <= Fraction(1) &&
          s.eta_discharge > Fraction(0) && s.eta_discharge <= Fraction(1))) {
        hold("HOLD_EFFICIENCY_DOMAIN");
    }
    if (charge > s.max_charge || discharge > s.max_discharge) hold("HOLD_STORAGE_RATE");
    const Fraction next = stock + delta_t * (s.eta_charge * charge - discharge / s.eta_discharge - self_loss);
    if (next < Fraction(0) || next > s.capacity) hold("HOLD_STORAGE_CAPACITY");
    return next;
}

static void uncertainty_moment(bool covariance_present) {
    if (!covariance_present) hold("HOLD_COVARIANCE_REQUIRED");
}

static void uncertainty_empirical(const std::string& a, const std::string& b, const std::string& required) {
    if (a != required || b != required) hold("HOLD_SAMPLE_ALIGNMENT_REQUIRED");
}

[[noreturn]] static void emit_aggregate_equilibrium_score() {
    hold("HOLD_AGGREGATE_SCORE_PROHIBITED");
}

static bool all_zero(const NodeMap& m) {
    for (const auto& [_, v] : m) if (v != Fraction(0)) return false;
    return true;
}

static std::string map_key(const NodeMap& m) {
    std::ostringstream os;
    bool first = true;
    for (const auto& [k, v] : m) {
        if (!first) os << ";";
        first = false;
        os << k << "=" << v.str();
    }
    return os.str();
}

static std::pair<bool, std::string> expect_hold(const std::string& code, const auto& fn) {
    try {
        fn();
    } catch (const HoldError& e) {
        return {e.code == code, e.code};
    }
    return {false, "NO_HOLD"};
}

static BalanceInput fixture_f01() {
    const Layer layer = Layer::Electricity;
    auto nodes = nodes_for(layer, {"E0", "E1"});
    std::vector<InternalEdge> edges{{"E01", layer, "E0", "E1", ""}};
    return BalanceInput{
        layer, "T0", nodes, edges, build_internal_incidence(nodes, edges),
        {qv(Fraction(15), layer), qv(Fraction(0), layer)},
        {qv(Fraction(5), layer), qv(Fraction(10), layer)},
        {qv(Fraction(0), layer), qv(Fraction(0), layer)},
        {qv(Fraction(10), layer)}
    };
}

static BalanceInput fixture_f02() {
    const Layer layer = Layer::Electricity;
    auto nodes = nodes_for(layer, {"E0"});
    BalanceInput x{
        layer, "T0", nodes, {}, Matrix(1),
        {qv(Fraction(0), layer)},
        {qv(Fraction(5), layer)},
        {qv(Fraction(0), layer)},
        {}
    };
    x.boundary_edges = {{"BIN", layer, "E0", "IMPORT"}};
    x.boundary_flow = {qv(Fraction(5), layer)};
    return x;
}

static std::pair<BalanceInput, Process> fixture_f03_gas() {
    const Layer layer = Layer::NaturalGas;
    auto nodes = nodes_for(layer, {"G0"});
    Process p{"GT", "PHYSICAL_CONVERSION", {{layer, "G0", Fraction(-80), "EV:gas-rate"}}, "SRC", "METHOD"};
    BalanceInput x{
        layer, "T0", nodes, {}, Matrix(1),
        {qv(Fraction(100), layer)},
        {qv(Fraction(20), layer)},
        {qv(Fraction(0), layer)},
        {}
    };
    x.process_contribution = process_coupling(p, Fraction(1), nodes, layer);
    return {x, p};
}

static BalanceInput fixture_f04_electricity() {
    const Layer layer = Layer::Electricity;
    auto nodes = nodes_for(layer, {"E0"});
    Process p{"GT", "PHYSICAL_CONVERSION", {{layer, "E0", Fraction(40), "EV:elec-rate"}}, "SRC", "METHOD"};
    BalanceInput x{
        layer, "T0", nodes, {}, Matrix(1),
        {qv(Fraction(0), layer)},
        {qv(Fraction(40), layer)},
        {qv(Fraction(0), layer)},
        {}
    };
    x.process_contribution = process_coupling(p, Fraction(1), nodes, layer);
    return x;
}

static BalanceInput fixture_f05_water() {
    const Layer layer = Layer::Freshwater;
    auto nodes = nodes_for(layer, {"W0"});
    Process p{"GT", "PHYSICAL_CONVERSION", {{layer, "W0", Fraction(-2), "EV:water-rate"}}, "SRC", "METHOD"};
    BalanceInput x{
        layer, "T0", nodes, {}, Matrix(1),
        {qv(Fraction(2), layer)},
        {qv(Fraction(0), layer)},
        {qv(Fraction(0), layer)},
        {}
    };
    x.process_contribution = process_coupling(p, Fraction(1), nodes, layer);
    return x;
}

static Storage fixture_f06_storage(Fraction capacity = Fraction(200), Fraction eta_charge = Fraction(9,10)) {
    return Storage{"S0", Layer::Electricity, "E0", capacity, Fraction(20), Fraction(20), eta_charge, Fraction(4,5)};
}

static BalanceInput fixture_f07_oil() {
    const Layer layer = Layer::CrudeOil;
    auto nodes = nodes_for(layer, {"O0", "O1", "O2"});
    std::vector<InternalEdge> edges{
        {"O01", layer, "O0", "O1", ""},
        {"O12", layer, "O1", "O2", ""}
    };
    return BalanceInput{
        layer, "T0", nodes, edges, build_internal_incidence(nodes, edges),
        {qv(Fraction(12), layer), qv(Fraction(0), layer), qv(Fraction(0), layer)},
        {qv(Fraction(0), layer), qv(Fraction(0), layer), qv(Fraction(12), layer)},
        {qv(Fraction(0), layer), qv(Fraction(0), layer), qv(Fraction(0), layer)},
        {qv(Fraction(12), layer), qv(Fraction(12), layer)}
    };
}

static std::pair<BalanceInput, BalanceInput> fixture_f08_desalination() {
    auto en = nodes_for(Layer::Electricity, {"E0"});
    auto wa = nodes_for(Layer::Freshwater, {"W0"});
    Process p{
        "DESAL", "PHYSICAL_CONVERSION",
        {
            {Layer::Electricity, "E0", Fraction(-6), "EV:desal-elec"},
            {Layer::Freshwater, "W0", Fraction(3), "EV:desal-water"}
        },
        "SRC", "METHOD"
    };
    BalanceInput e{
        Layer::Electricity, "T0", en, {}, Matrix(1),
        {qv(Fraction(6), Layer::Electricity)},
        {qv(Fraction(0), Layer::Electricity)},
        {qv(Fraction(0), Layer::Electricity)},
        {}
    };
    e.process_contribution = process_coupling(p, Fraction(1), en, Layer::Electricity);
    BalanceInput w{
        Layer::Freshwater, "T0", wa, {}, Matrix(1),
        {qv(Fraction(0), Layer::Freshwater)},
        {qv(Fraction(3), Layer::Freshwater)},
        {qv(Fraction(0), Layer::Freshwater)},
        {}
    };
    w.process_contribution = process_coupling(p, Fraction(1), wa, Layer::Freshwater);
    return {e,w};
}

struct CaseResult {
    std::string id;
    bool passed;
    std::string semantic;
};

static CaseResult cr(int i, bool pass, std::string semantic) {
    std::ostringstream id;
    id << "V";
    if (i < 10) id << "0";
    id << i;
    return {id.str(), pass, std::move(semantic)};
}

static std::vector<CaseResult> run_validation_matrix_cpp() {
    std::vector<CaseResult> r;
    r.reserve(40);

    {
        const auto f = fixture_f01();
        try { validate_internal_incidence(f.B, f.nodes, f.internal_edges); r.push_back(cr(1,true,"PASS")); }
        catch (...) { r.push_back(cr(1,false,"UNEXPECTED_HOLD")); }
    }
    {
        const auto x = resource_balance_residual(fixture_f01());
        r.push_back(cr(2, all_zero(x), all_zero(x) ? "ZERO_RESIDUAL" : "NONZERO_RESIDUAL"));
    }
    {
        const auto x = resource_balance_residual(fixture_f02());
        r.push_back(cr(3, all_zero(x), all_zero(x) ? "ZERO_RESIDUAL" : "NONZERO_RESIDUAL"));
    }
    {
        const auto [f,_] = fixture_f03_gas();
        const auto x = resource_balance_residual(f);
        r.push_back(cr(4, all_zero(x), all_zero(x) ? "ZERO_RESIDUAL" : "NONZERO_RESIDUAL"));
    }
    {
        const auto x = resource_balance_residual(fixture_f04_electricity());
        r.push_back(cr(5, all_zero(x), all_zero(x) ? "ZERO_RESIDUAL" : "NONZERO_RESIDUAL"));
    }
    {
        const auto x = resource_balance_residual(fixture_f05_water());
        r.push_back(cr(6, all_zero(x), all_zero(x) ? "ZERO_RESIDUAL" : "NONZERO_RESIDUAL"));
    }
    {
        try {
            const auto next = storage_transition(fixture_f06_storage(), Fraction(100), Fraction(10), Fraction(4));
            r.push_back(cr(7, next == Fraction(104), next == Fraction(104) ? "STORAGE_104" : next.str()));
        } catch (const HoldError& e) { r.push_back(cr(7,false,e.code)); }
    }
    {
        const auto x = resource_balance_residual(fixture_f07_oil());
        r.push_back(cr(8, all_zero(x), all_zero(x) ? "ZERO_RESIDUAL" : "NONZERO_RESIDUAL"));
    }
    {
        const auto [e,w] = fixture_f08_desalination();
        const bool z = all_zero(resource_balance_residual(e)) && all_zero(resource_balance_residual(w));
        r.push_back(cr(9,z,z ? "ZERO_RESIDUAL" : "NONZERO_RESIDUAL"));
    }
    {
        bool ok = true;
        for (const auto layer : {Layer::Electricity,Layer::NaturalGas,Layer::CrudeOil,Layer::Freshwater}) {
            auto nodes = nodes_for(layer,{layer_name(layer)+"0"});
            BalanceInput x{layer,"T0",nodes,{},Matrix(1),
                {qv(Fraction(7),layer)},{qv(Fraction(7),layer)},{qv(Fraction(0),layer)},{}};
            ok = ok && all_zero(resource_balance_residual(x));
        }
        r.push_back(cr(10,ok,ok ? "FOUR_LAYER_ZERO" : "NONZERO_RESIDUAL"));
    }
    {
        auto f=fixture_f01();
        f.B={{1},{-1}};
        const auto [ok,obs]=expect_hold("HOLD_MANIFEST_MISMATCH",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(11,ok,obs));
    }
    {
        auto f=fixture_f02();
        f.boundary_edges[0].direction="SIDEWAYS";
        const auto [ok,obs]=expect_hold("HOLD_BOUNDARY_DIRECTION",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(12,ok,obs));
    }
    {
        auto [f,p]=fixture_f03_gas();
        p.coefficients[0].coefficient=Fraction(80);
        f.process_contribution=process_coupling(p,Fraction(1),f.nodes,Layer::NaturalGas);
        const auto x=resource_balance_residual(f);
        r.push_back(cr(13,!all_zero(x),!all_zero(x) ? "NONZERO_RESIDUAL" : "ZERO_RESIDUAL"));
    }
    {
        auto f=fixture_f01();
        f.production[0]=qv(Fraction(1),Layer::Freshwater);
        const auto [ok,obs]=expect_hold("HOLD_UNIT_MISMATCH",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(14,ok,obs));
    }
    {
        auto f=fixture_f01();
        f.production[0]=qv(Fraction(15),Layer::Electricity,Kind::Stock);
        const auto [ok,obs]=expect_hold("HOLD_UNIT_MISMATCH",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(15,ok,obs));
    }
    {
        const auto layer=Layer::NaturalGas;
        auto nodes=nodes_for(layer,{"G0"});
        BalanceInput f{layer,"T0",nodes,{},Matrix(1),
            {qv(Fraction(1),layer,Kind::Rate,"T0",Status::Observed,Space::Physical,"HHV")},
            {qv(Fraction(1),layer,Kind::Rate,"T0",Status::Observed,Space::Physical,"LHV")},
            {qv(Fraction(0),layer,Kind::Rate,"T0",Status::Observed,Space::Physical,"HHV")},
            {}};
        const auto [ok,obs]=expect_hold("HOLD_HHV_LHV_BASIS_MISMATCH",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(16,ok,obs));
    }
    {
        auto f=fixture_f02();
        f.demand[0].interval="T1";
        const auto [ok,obs]=expect_hold("HOLD_TIME_BASIS_MISMATCH",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(17,ok,obs));
    }
    {
        const auto [ok,obs]=expect_hold("HOLD_STORAGE_CAPACITY",[&]{
            (void)storage_transition(fixture_f06_storage(Fraction(103)),Fraction(100),Fraction(10),Fraction(4));
        });
        r.push_back(cr(18,ok,obs));
    }
    {
        const auto [ok,obs]=expect_hold("HOLD_STORAGE_RATE",[&]{
            (void)storage_transition(fixture_f06_storage(),Fraction(100),Fraction(21),Fraction(4));
        });
        r.push_back(cr(19,ok,obs));
    }
    {
        const auto [ok,obs]=expect_hold("HOLD_STORAGE_RATE",[&]{
            (void)storage_transition(fixture_f06_storage(),Fraction(100),Fraction(10),Fraction(21));
        });
        r.push_back(cr(20,ok,obs));
    }
    {
        const auto [ok,obs]=expect_hold("HOLD_EFFICIENCY_DOMAIN",[&]{
            (void)storage_transition(fixture_f06_storage(Fraction(200),Fraction(0)),Fraction(100),Fraction(10),Fraction(4));
        });
        r.push_back(cr(21,ok,obs));
    }
    {
        const QValue zero=qv(Fraction(0),Layer::Electricity);
        const QValue missing=qv(std::nullopt,Layer::Electricity,Kind::Rate,"T0",Status::Missing);
        bool zero_ok=false;
        try { zero_ok=qualified_value_guard(zero).value.value()==Fraction(0); } catch (...) {}
        const auto [h,obs]=expect_hold("HOLD_MISSING_INPUT",[&]{ (void)qualified_value_guard(missing); });
        r.push_back(cr(22,zero_ok&&h,obs));
    }
    {
        auto v=qv(Fraction(3),Layer::Electricity,Kind::Rate,"T0",Status::Conflicted);
        const auto [ok,obs]=expect_hold("HOLD_CONFLICTED_INPUT",[&]{ (void)qualified_value_guard(v); });
        r.push_back(cr(23,ok,obs));
    }
    {
        auto v=qv(Fraction(3),Layer::Electricity,Kind::Rate,"T0",Status::Stale);
        const auto [ok,obs]=expect_hold("HOLD_STALE_INPUT",[&]{ (void)qualified_value_guard(v); });
        r.push_back(cr(24,ok,obs));
    }
    {
        auto v=qv(Fraction(3),Layer::Electricity,Kind::Rate,"T0",Status::Derived);
        v.transform_chain={"imputation:model-x"};
        const auto [ok,obs]=expect_hold("HOLD_IMPUTED_FLAG_ERASED",[&]{ (void)qualified_value_guard(v,GuardPolicy::AllowImputedWithFlag); });
        r.push_back(cr(25,ok,obs));
    }
    {
        const auto [ok,obs]=expect_hold("HOLD_COVARIANCE_REQUIRED",[&]{ uncertainty_moment(false); });
        r.push_back(cr(26,ok,obs));
    }
    {
        const auto [ok,obs]=expect_hold("HOLD_SAMPLE_ALIGNMENT_REQUIRED",[&]{ uncertainty_empirical("A","B","A"); });
        r.push_back(cr(27,ok,obs));
    }
    {
        auto f=fixture_f01();
        f.internal_edges[0].loss_model_ref="LOSS";
        f.B=build_internal_incidence(f.nodes,f.internal_edges);
        f.loss[0]=qv(Fraction(1),Layer::Electricity);
        const auto [ok,obs]=expect_hold("HOLD_DOUBLE_COUNT_LOSS",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(28,ok,obs));
    }
    {
        auto [f,p]=fixture_f03_gas();
        p.coefficients[0].evidence_ref="";
        const auto [ok,obs]=expect_hold("HOLD_PROCESS_EVIDENCE",[&]{
            (void)process_coupling(p,Fraction(1),f.nodes,Layer::NaturalGas);
        });
        r.push_back(cr(29,ok,obs));
    }
    {
        auto [f,p]=fixture_f03_gas();
        p.process_class="CORRELATION";
        const auto [ok,obs]=expect_hold("HOLD_CAUSALITY",[&]{
            (void)process_coupling(p,Fraction(1),f.nodes,Layer::NaturalGas);
        });
        r.push_back(cr(30,ok,obs));
    }
    {
        auto f=fixture_f01(); f.production[0].space=Space::Audit;
        const auto [ok,obs]=expect_hold("HOLD_AUDIT_PHYSICAL_MIX",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(31,ok,obs));
    }
    {
        auto f=fixture_f01(); f.production[0].space=Space::Evidence;
        const auto [ok,obs]=expect_hold("HOLD_AUDIT_PHYSICAL_MIX",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(32,ok,obs));
    }
    {
        auto f=fixture_f01(); f.production[0].space=Space::Stress;
        const auto [ok,obs]=expect_hold("HOLD_STRESS_PHYSICAL_MIX",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(33,ok,obs));
    }
    {
        const auto [ok,obs]=expect_hold("HOLD_AGGREGATE_SCORE_PROHIBITED",[&]{ emit_aggregate_equilibrium_score(); });
        r.push_back(cr(34,ok,obs));
    }
    {
        auto f=fixture_f01(); f.nodes[0].manifest_version="V2";
        const auto [ok,obs]=expect_hold("HOLD_TOPOLOGY_CHANGED",[&]{ (void)resource_balance_residual(f); });
        r.push_back(cr(35,ok,obs));
    }
    {
        const auto a=map_key(resource_balance_residual(fixture_f01()));
        const auto b=map_key(resource_balance_residual(fixture_f01()));
        r.push_back(cr(36,a==b,a==b ? "DETERMINISTIC_EQUAL" : "DETERMINISTIC_MISMATCH"));
    }
    {
        const auto base=resource_balance_residual(fixture_f01());
        const Layer layer=Layer::Electricity;
        auto nodes=nodes_for(layer,{"E1","E0"});
        std::vector<InternalEdge> edges{{"E01",layer,"E0","E1",""}};
        BalanceInput p{
            layer,"T0",nodes,edges,build_internal_incidence(nodes,edges),
            {qv(Fraction(0),layer),qv(Fraction(15),layer)},
            {qv(Fraction(10),layer),qv(Fraction(5),layer)},
            {qv(Fraction(0),layer),qv(Fraction(0),layer)},
            {qv(Fraction(10),layer)}
        };
        const auto perm=resource_balance_residual(p);
        r.push_back(cr(37,base==perm,base==perm ? "PERMUTATION_INVARIANT" : "PERMUTATION_MISMATCH"));
    }
    {
        const auto zero=qv(Fraction(0),Layer::Electricity);
        const auto missing=qv(std::nullopt,Layer::Electricity,Kind::Rate,"T0",Status::Missing);
        bool z=false; bool m=false;
        try { z=qualified_value_guard(zero).value.value()==Fraction(0); } catch (...) {}
        try { (void)qualified_value_guard(missing); } catch (const HoldError& e) { m=e.code=="HOLD_MISSING_INPUT"; }
        r.push_back(cr(38,z&&m,z&&m ? "ZERO_DISTINCT_MISSING" : "DISTINCTION_FAIL"));
    }
    {
        auto [f,p]=fixture_f03_gas();
        auto enodes=nodes_for(Layer::Electricity,{"E0"});
        const auto out=process_coupling(p,Fraction(1),enodes,Layer::Electricity);
        r.push_back(cr(39,all_zero(out),all_zero(out) ? "ZERO_COUPLING" : "NONZERO_COUPLING"));
    }
    {
        const auto a=resource_balance_residual(fixture_f01());
        (void)resource_balance_residual(fixture_f07_oil());
        const auto b=resource_balance_residual(fixture_f01());
        r.push_back(cr(40,a==b,a==b ? "HISTORY_INDEPENDENT" : "HISTORY_DEPENDENT"));
    }

    return r;
}

static std::string json_escape(const std::string& s) {
    std::string out;
    for (char c : s) {
        if (c == '"' || c == '\\') out += '\\';
        out += c;
    }
    return out;
}

} // namespace eqprs

int main() {
    using namespace eqprs;
    const auto results = run_validation_matrix_cpp();
    std::size_t pass_count = 0;
    for (const auto& x : results) {
        if (x.passed) ++pass_count;
        std::cout
            << "{\"id\":\"" << json_escape(x.id)
            << "\",\"passed\":" << (x.passed ? "true" : "false")
            << ",\"semantic\":\"" << json_escape(x.semantic)
            << "\"}\n";
    }
    std::cout << "CPP_MATRIX=" << pass_count << "/" << results.size() << "\n";
    return pass_count == 40 && results.size() == 40 ? EXIT_SUCCESS : EXIT_FAILURE;
}
