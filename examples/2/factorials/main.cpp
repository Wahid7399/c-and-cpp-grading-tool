#include <iostream>
#include "extra.cpp"
using namespace std;

int main() {
    int num = 0;
    cout << "Enter a number: ";
    cin >> num;
    if (num < 0) {
        cout << "Factorial is not defined for negative numbers." << endl;
    } else {
        cout << "Factorial of " << num << " is " << factorial(num) << endl;
    }
    return 0;
}
