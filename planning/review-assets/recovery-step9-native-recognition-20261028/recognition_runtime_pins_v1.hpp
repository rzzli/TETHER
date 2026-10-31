#pragma once
// Prospective recognition DATA ONLY header. Source/pure metadata work does not authorize payload access or execution.
inline constexpr ModulePin APPROVED_RUNTIME_DLLS[] = {
    {L"ggml-base.dll", "84e3057e6fe2c581a9d194d27e5510b1a71723074e01dfb9b34926e4d5af52f3", 803840ull},
    {L"ggml.dll", "2a49a0f2d3c58b182bfa5267950cef2e4f3378a12e9ebbc6b36554bf5ca016ba", 78848ull},
    {L"llama.dll", "166e8de1bd07573dc0f51ab1f429ab5df0d08492e7302bbe41a39014248f5e6d", 3581952ull},
    {L"ggml-cpu-x64.dll", "d402f7ff9cb7e27224ead72a83ae064653f60d237ef82a10697b21be5a6bd472", 909824ull},
    {L"libomp.dll", "a12116ba72d1d6820407cf30be23da04ce79d6bb8a71a5ee71759c5a1faa6f1c", 768000ull},
};
inline constexpr wchar_t R09_RUNTIME_DIRECTORY[] = L"D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\runtime";
inline constexpr wchar_t R09_CPU_BASENAME[] = L"ggml-cpu-x64.dll";
inline constexpr bool R09_LIBOMP_REQUIRED = true;
inline constexpr char R09_CPU_REGISTRY_NAME[] = "CPU";
inline constexpr char R09_CPU_DEVICE_NAME[] = "CPU";
inline constexpr char R09_EXPECTED_LLAMA_VERSION[] = "0.7.0-dev";
// Prospective finite System32 prediction; no complete historical loaded inventory.
inline constexpr const wchar_t* R09_SYSTEM_DLL_NAMES[] = {
    L"ntdll.dll",
    L"kernel32.dll",
    L"kernelbase.dll",
    L"ucrtbase.dll",
    L"msvcp140.dll",
    L"vcruntime140.dll",
    L"vcruntime140_1.dll",
    L"advapi32.dll",
    L"psapi.dll",
    L"sechost.dll",
    L"rpcrt4.dll",
    L"msvcrt.dll",
    L"bcrypt.dll",
    L"bcryptprimitives.dll",
    L"cryptbase.dll",
    L"cryptsp.dll",
};
inline constexpr FilePin R09_PACK = {L"D:\\Projects\\drug_target_agents\\data\\cache\\r09-native-recognition-pack-v2-20261028T183647Z\\recognition.pack", "f75ab9937c57b5f03c2234643a8a9c91cda852ca0cca0de0478369f793e57e5f", 259867ull};
inline constexpr FilePin R09_SHARDS[3] = {
    {L"D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf", "a09ea5e7b1eafb1b30b241726c3cc3c905c96f14ad41e246ffa5f44e53904f68", 3991999872ull},
    {L"D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\qwen2.5-14b-instruct-q4_k_m-00002-of-00003.gguf", "21b9457d079680d284e90ef69607c4b2d8ef64a09d4729cb7b5e1357bdba41ae", 3989373504ull},
    {L"D:\\Projects\\drug_target_agents\\data\\cache\\approved-native-mirror-20261028T004531Z\\qwen2.5-14b-instruct-q4_k_m-00003-of-00003.gguf", "c8d37006760a387a35216e070e6664d7da927f10be8eb870fef2e3d4833d9976", 1006737120ull},
};
inline constexpr bool R09_RECOGNITION_ENABLED = true;

inline constexpr char R09_RECOGNITION_POLICY_ID[] = "trusted-System32-recognition-v1";
inline constexpr char R09_RECOGNITION_POLICY_SHA256[] = "4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713";
inline constexpr uint64_t R09_COOPERATIVE_WORK_MS = 117000ull;
