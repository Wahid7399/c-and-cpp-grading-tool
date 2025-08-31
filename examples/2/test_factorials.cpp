#include <iostream>

using namespace std;

// FUNCTION TEST

TEST_CASE("#1 factorial basic values. Score: 15") {
    CHECK(factorial(0) == 1);
    CHECK(factorial(1) == 1);
    CHECK(factorial(2) == 2);
    CHECK(factorial(3) == 6);
    CHECK(factorial(10) == 3628800);
}

TEST_CASE("#2 factorial grows quickly. Score: 5") {
    CHECK(factorial(5) == 120);
    CHECK(factorial(6) == 720);
}

// CIN/COUT IO TEST

TEST_CASE("#3 main: valid input prints factorial. Score: 5") {
    auto out = RUN_IO("5\n");
    CHECK(out.find("Enter a number: ") != -1);
    CHECK(out.find("Factorial of 5 is 120") != -1);
}

TEST_CASE("#4 main: negative input handled by message. Score: 5") {
    auto out = RUN_IO("-3\n");
    CHECK(out.find("Enter a number: ") != -1);
    CHECK(out.find("Factorial is not defined for negative numbers.") != -1);
}