// All correctly initialized — expect 0 findings

// Scalar initializations
int a = 0;
int b{};
int c{42};
int d(0);
float pi = 3.14f;
bool flag = false;
double val = 1.0;
char ch = 'x';

// Array initializations
float arr[10]{};
float arr2[10] = {0};
int grid[3][3] = {};
char buf[256]{};

// Pointer initializations
int *p = nullptr;
int *q{};
const char *str = "hello";
void *vp = nullptr;

// References (compiler enforces init)
const int &ref = a;
int &mref = a;

// For-loop variables (not declarations)
void foo() {
  for (int i = 0; i < 10; ++i) {
  }
  for (auto &x : arr) {
  }
  for (const auto &item : arr) {
  }
  for (unsigned j = 0; j < 5; ++j) {
  }
}

// Extern declarations (no init needed)
extern int external_var;
extern const double ext_const;

// Class/struct with initialized members
struct Good {
  int x_{};
  float y_ = 0.0f;
  int *p_ = nullptr;
  bool active_ = false;
  std::string name_{};
  std::vector<int> data_{};
};

// Forward declarations (not variable decls)
class ForwardDeclared;
struct AnotherForward;
enum SomeEnum;

// Typedef and using (not variable decls)
typedef int MyInt;
using MyFloat = float;

// Correctly initialized class types
std::vector<int> vec{};
std::string str2{};
std::map<int, std::string> m{};
MyClass obj{};

// Correctly initialized multi-word types
unsigned long ul = 0;
signed int si = 0;
long long ll = 0LL;
unsigned long long ull = 0ULL;

// CUDA with initializers
__shared__ int shared_val = 0;
__device__ float dev_val{};

// Function declarations (not variable decls)
int compute(int x, int y);
void process(const std::string &input);
static inline int helper(int n) { return n + 1; }

// Constexpr (always initialized)
constexpr int kMaxSize = 100;
constexpr double kPi = 3.14159;

// Static class members (definitions with init)
int MyClass::static_member = 0;

// Return statements
int bar() { return 42; }

// Enum definitions
enum Color { RED, GREEN, BLUE };
enum class Direction { UP, DOWN, LEFT, RIGHT };

// Template function
template <typename T> T identity(T val) { return val; }

// Structured bindings
auto [x, y] = std::make_pair(1, 2);

// Multi-line initialized
const volatile int32_t reading = 0;

// Inline variable (C++17)
inline int inlined = 5;

// New expressions (not declarations)
void allocate() {
  auto *obj = new MyClass();
  delete obj;
}
