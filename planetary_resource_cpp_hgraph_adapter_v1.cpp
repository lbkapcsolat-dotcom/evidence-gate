#include <hgraph/lib/std/standard_types.h>
#include <hgraph/lib/testing/eval_node.h>
#include <hgraph/types/graph_wiring.h>
#include <hgraph/types/operator_dispatch.h>
#include <hgraph/types/static_node.h>

#include <cstdlib>
#include <cstdint>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#define main eqprs_standalone_main_disabled_for_hgraph_adapter
#include "planetary_resource_cpp_kernel_v1.cpp"
#undef main

namespace eqprs_hgraph_adapter {

using namespace hgraph;

struct planetary_resource_validation_case
    : Operator<"equilibrium.planetary_resource.validation_case",
               In<"case_id", TS<Int>>,
               Out<TS<Str>>>
{
};

struct planetary_resource_validation_case_cpp
{
    static constexpr auto name = "planetary_resource_validation_case_cpp";

    static void eval(In<"case_id", TS<Int>> case_id, Out<TS<Str>> out)
    {
        const auto i = static_cast<std::int64_t>(case_id.value());
        if (i < 1 || i > 40)
        {
            throw std::out_of_range("case_id must be in [1,40]");
        }

        const auto results = eqprs::run_validation_matrix_cpp();
        const auto &row = results.at(static_cast<std::size_t>(i - 1));
        if (!row.passed)
        {
            throw std::runtime_error("independent C++ domain case failed: " + row.id);
        }
        out.set(Str{row.semantic});
    }
};

struct planetary_resource_validation_graph
{
    static constexpr auto name = "planetary_resource_validation_graph";

    static Port<TS<Str>> compose(Wiring &w, Port<TS<Int>> case_id)
    {
        return wire<planetary_resource_validation_case>(w, case_id);
    }
};

}  // namespace eqprs_hgraph_adapter

int main()
{
    using namespace hgraph;
    using namespace eqprs_hgraph_adapter;

    (void)stdlib::register_standard_types();
    register_overload<planetary_resource_validation_case,
                      planetary_resource_validation_case_cpp>();

    const auto standalone = eqprs::run_validation_matrix_cpp();
    if (standalone.size() != 40)
    {
        std::cerr << "STANDALONE_COUNT_MISMATCH\n";
        return EXIT_FAILURE;
    }

    std::size_t pass = 0;
    for (std::size_t i = 0; i < standalone.size(); ++i)
    {
        const auto case_id = static_cast<Int>(i + 1);
        const auto out = testing::eval_node<planetary_resource_validation_graph>(
            std::vector<std::optional<Int>>{case_id});

        if (out.size() != 1 || !out.front().has_value())
        {
            std::cerr << standalone[i].id << " HGRAPH_NO_OUTPUT\n";
            return EXIT_FAILURE;
        }

        const std::string observed = out.front().value();
        const bool equal = standalone[i].passed && observed == standalone[i].semantic;
        std::cout
            << "{\"id\":\"" << standalone[i].id
            << "\",\"standalone\":\"" << eqprs::json_escape(standalone[i].semantic)
            << "\",\"cpp_hgraph_adapter\":\"" << eqprs::json_escape(observed)
            << "\",\"equal\":" << (equal ? "true" : "false")
            << "}\n";

        if (!equal)
        {
            std::cerr << standalone[i].id << " ADAPTER_PARITY_FAIL\n";
            return EXIT_FAILURE;
        }
        ++pass;
    }

    std::cout << "CPP_HGRAPH_ADAPTER_MATRIX=" << pass << "/40\n";
    return pass == 40 ? EXIT_SUCCESS : EXIT_FAILURE;
}
