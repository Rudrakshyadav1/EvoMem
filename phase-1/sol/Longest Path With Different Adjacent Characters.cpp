// # Longest Path With Different Adjacent Characters
// description:[
//     You are given a tree (i.e. a connected, undirected graph that has no cycles) rooted at node 0 consisting of n nodes numbered from 0 to n - 1. The tree is represented by a 0-indexed array parent of size n, where parent[i] is the parent of node i. Since node 0 is the root, parent[0] == -1.
// You are also given a string s of length n, where s[i] is the character assigned to node i.
// Return the length of the longest path in the tree such that no pair of adjacent nodes on the path have the same character assigned to them.
// ]

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cassert>

using namespace std;

class Solution {
private:
    vector<vector<int>> adj;
    int ans = 0;

    int recurr(int u, const string &s) {
        int longest = 0;
        int s_longest = 0;

        for (int v : adj[u]) {
            int child = recurr(v, s);
            if (s[v] != s[u]) {
                if (child > longest) {
                    s_longest = longest;
                    longest = child;
                } else if (child > s_longest) {
                    s_longest = child;
                }
            }
        }

        ans = max(ans, 1 + longest + s_longest);
        return 1 + longest;
    }

public:
    int longestPath(vector<int>& parent, string s) {
        int n = parent.size();
        if (n == 0) return 0;

        adj.assign(n, vector<int>());
        ans = 0;

        for (int i = 0; i < n; i++) {
            if (parent[i] != -1) {
                adj[parent[i]].push_back(i);
            }
        }

        recurr(0, s);
        return ans;
    }
};

int main() {
    Solution sol;

    // Test Case 1
    {
        vector<int> parent = {-1, 0, 0, 0};
        string s = "aabc";
        int result = sol.longestPath(parent, s);
        cout << "Test Case 1: " << result << " (Expected: 3)" << endl;
        assert(result == 3);
    }

    // Test Case 2
    {
        vector<int> parent = {-1, 0, 0, 1, 1, 2};
        string s = "abacbe";
        int result = sol.longestPath(parent, s);
        cout << "Test Case 2: " << result << " (Expected: 3)" << endl;
        assert(result == 3);
    }

    // Test Case 3: Single node
    {
        vector<int> parent = {-1};
        string s = "a";
        int result = sol.longestPath(parent, s);
        cout << "Test Case 3 (Single node): " << result << " (Expected: 1)" << endl;
        assert(result == 1);
    }

    // Test Case 4: All same characters
    {
        vector<int> parent = {-1, 0, 1, 2};
        string s = "aaaa";
        int result = sol.longestPath(parent, s);
        cout << "Test Case 4 (All same chars): " << result << " (Expected: 1)" << endl;
        assert(result == 1);
    }

    // Test Case 5: Star graph
    {
        vector<int> parent = {-1, 0, 0, 0, 0};
        string s = "abcde";
        int result = sol.longestPath(parent, s);
        cout << "Test Case 5 (Star graph): " << result << " (Expected: 3)" << endl;
        assert(result == 3);
    }

    cout << "All tests passed successfully!" << endl;
    return 0;
}
