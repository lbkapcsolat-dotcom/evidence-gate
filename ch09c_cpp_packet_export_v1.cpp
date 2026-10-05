#define main ch09a_cpp_hgraph_main_disabled_for_packet_export
#include "ch09a_babai_eq64_cpp_hgraph_replay_v1.cpp"
#undef main

#include <cstdlib>
#include <iostream>

int main()
{
    for (int state = 0; state < 64; ++state)
    {
        std::cout << ch09a::record_json(state) << "\n";
    }
    return EXIT_SUCCESS;
}
