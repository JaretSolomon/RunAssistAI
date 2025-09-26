// Domain.cpp
// Minimal domain validation/fix (demo). Extend with real JSON parsing later.

#include <string>

namespace domain {

// Very naive: if no "rest" mention, append an "adjustments" hint.
static std::string ensureRestHint(const std::string& json) {
    if (json.find("\"rest\"") != std::string::npos) return json;
    if (!json.empty() && json.back() == '}') {
        std::string s = json; s.pop_back();
        s += R"(,"adjustments":["insert_rest_day_suggestion"]})";
        return s;
    }
    return json;
}

std::string checkAndFixPlan(const std::string& json) {
    if (json.empty() || json == "{}") return "{\"error\":\"invalid plan\"}";
    // TODO: parse & enforce rules.
    return ensureRestHint(json);
}

} // namespace domain
