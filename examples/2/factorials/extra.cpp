
#pragma once

// Recursive function to calculate factorial
long long factorial(int n) {
    if (n == 0 || n == 1) // base case
        return 1;
    return n * factorial(n - 1); // recursive step
}
