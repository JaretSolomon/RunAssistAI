// main.cpp
// CLI demo: read a simple goal -> call core pipeline -> print JSON plan.

#include <iostream>
#include <string>

// Facade API
namespace core {
    bool        init(const std::string& model_path, int n_ctx = 2048, int n_gpu_layers = 0);
    std::string generatePlan(const std::string& user_profile_json, int max_tokens = 512);
    void        shutdown();
}

static std::string buildMinimalProfile(const std::string& goal) {
    // Keep it tiny; extend with more fields as you like.
    return std::string("{\"goal\":\"") + goal +
           "\",\"horizon_weeks\":8,\"sessions_per_week\":4}";
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cout << "Usage: ./workout <path_to_model.gguf>\n";
        return 0;
    }
    const std::string model_path = argv[1];

    if (!core::init(model_path, /*n_ctx*/2048, /*n_gpu_layers*/0)) {
        std::cerr << "Model init failed.\n"; return 1;
    }

    std::cout << "Enter goal (e.g., \"5K under 25:00\"): ";
    std::string goal; std::getline(std::cin, goal);

    const std::string profile = buildMinimalProfile(goal);
    const std::string plan    = core::generatePlan(profile, /*max_tokens*/512);

    std::cout << "\n=== Training Plan (JSON) ===\n" << plan << "\n";

    core::shutdown();
    return 0;
}
