// CoreFacade.cpp
// Orchestrates: buildPrompt -> lw::generate -> extractFirstJson -> domain check.

#include <string>
#include <cstring>
#include <iostream>

// ---- Forward decls (from other TUs) ----
namespace lw {
    bool        init(const std::string& model_path, int n_ctx, int n_gpu_layers);
    std::string generate(const std::string& prompt, int max_tokens);
    void        shutdown();
}
namespace prompt {
    std::string buildPrompt(const std::string& profile_json);
}
namespace jsonutil {
    std::string extractFirstJson(const std::string& text);
    bool        looksLikeJson(const std::string& s);
}
namespace domain {
    std::string checkAndFixPlan(const std::string& json);
}

// ---- Public facade API (C++ namespace) ----
namespace core {

static bool g_inited = false;

bool init(const std::string& model_path, int n_ctx = 2048, int n_gpu_layers = 0) {
    g_inited = lw::init(model_path, n_ctx, n_gpu_layers);
    return g_inited;
}

std::string generatePlan(const std::string& user_profile_json, int max_tokens = 10240) {
    if (!g_inited) return "{}";
    const std::string promptStr = prompt::buildPrompt(user_profile_json);
    const std::string raw       = lw::generate(promptStr, max_tokens);
    std::cerr << "[diag] raw.size=" << raw.size()
          << " head=" << raw.substr(0, 2000) << "\n";
    std::string cand            = jsonutil::extractFirstJson(raw);
    if (!jsonutil::looksLikeJson(cand)) cand = "{}";
    return domain::checkAndFixPlan(cand);
}

void shutdown() { lw::shutdown(); g_inited = false; }

} // namespace core
