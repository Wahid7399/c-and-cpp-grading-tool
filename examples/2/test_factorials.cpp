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
