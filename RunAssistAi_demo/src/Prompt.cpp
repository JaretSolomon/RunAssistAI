// Prompt.cpp
// Build LLM input prompt (system constraints + user profile JSON).

#include <string>

namespace prompt {
std::string buildPrompt(const std::string& profile_json) {
    static const char* kSys =
        "<|system|>\n"
        "You are a certified strength & conditioning coach.\n"
        "Follow these constraints:\n"
        "- progressive overload <= 10% per week\n"
        "- 1-2 rest days per week\n"
        "- deload every 4th week\n"
        "- respect injuries (swap with low-impact work)\n\n"
        "Your output MUST be a valid JSON object.\n"
        "Do not write any explanations, markdown, or text outside JSON.\n"
        "JSON schema:\n"
        "{\n"
        "  \"goal\": string,\n"
        "  \"weeks\": [\n"
        "    {\"week\": number, \"sessions\": [string, ...]}\n"
        "  ],\n"
        "  \"rest_days\": [string, ...]\n"
        "}\n";

    std::string p;
    p.reserve(512 + profile_json.size());
    p += kSys;
    p += "\n<|user|>\n";
    p += "User profile JSON:\n";
    p += profile_json;
    p += "\n\nReturn ONLY the training plan as JSON.";
    p += "\n<|assistant|>\n"; // assistant的起始符
    return p;
}
}