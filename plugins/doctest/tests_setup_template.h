#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest.h"
#include <sstream>
#include <iostream>

#define main DOCTEST_PROGRAM_MAIN
#include "[DOCTEST_MAIN_FILE_PATH]"
#undef main


static std::string RUN_IO(std::string in_text) {
    std::istringstream fake_in(in_text);
    std::ostringstream fake_out;

    // save originals
    std::streambuf* cin_old = std::cin.rdbuf();
    std::streambuf* cout_old = std::cout.rdbuf();

    // redirect
    std::cin.rdbuf(fake_in.rdbuf());
    std::cout.rdbuf(fake_out.rdbuf());

    // call the program's real main (renamed)
    DOCTEST_PROGRAM_MAIN();

    // restore
    std::cin.rdbuf(cin_old);
    std::cout.rdbuf(cout_old);

    return fake_out.str();
}
