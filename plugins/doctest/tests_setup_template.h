#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest.h"
#include <sstream>
#include <iostream>
#include <string>
#include <unistd.h>
#include <cstdio>
#include <vector>

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

    // call the program's real main (renamed), only if declared
    #ifdef DOCTEST_PROGRAM_MAIN
        DOCTEST_PROGRAM_MAIN();
    #endif

    // restore
    std::cin.rdbuf(cin_old);
    std::cout.rdbuf(cout_old);

    return fake_out.str();
}

static int saved_stdout_fd;
static int pipe_fd[2];

static void START_CAPTURE() {
    fflush(stdout);
    pipe(pipe_fd);
    saved_stdout_fd = dup(fileno(stdout));
    dup2(pipe_fd[1], fileno(stdout));
    close(pipe_fd[1]);
}

static std::string END_CAPTURE() {
    fflush(stdout);
    dup2(saved_stdout_fd, fileno(stdout));
    close(saved_stdout_fd);

    std::string out;
    char buf[256];
    ssize_t n;
    while ((n = read(pipe_fd[0], buf, sizeof(buf))) > 0) {
        out.append(buf, n);
    }
    close(pipe_fd[0]);
    return out;
}
