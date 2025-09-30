cmake_minimum_required(VERSION 3.16)
project(WorkoutApp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(LLAMA_DIR ${CMAKE_SOURCE_DIR}/third_party/llama.cpp)

add_subdirectory(${LLAMA_DIR} build_llama)

add_executable(workout
    src/main.cpp
    src/CoreFacade.cpp
    src/Prompt.cpp
    src/JsonUtil.cpp
    src/Domain.cpp
    src/LlamaWrapper.cpp
)

target_include_directories(workout PRIVATE
    ${LLAMA_DIR}
    ${CMAKE_SOURCE_DIR}/src
)

target_link_libraries(workout PRIVATE llama)
