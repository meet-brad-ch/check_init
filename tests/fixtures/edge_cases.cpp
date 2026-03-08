// Edge cases for the scanner

// CUDA qualifiers — should be flagged
__shared__ int shared_arr[64];
__device__ float dev_var;

// Custom/std types — should be flagged
std::vector<int> v;
std::string s;
std::map<int, float> m;
MyCustomType obj;
helm::Perception perception;

// Function pointers — should be flagged
void (*func_ptr)(int);

// Multi-line with qualifiers — should be flagged
const volatile int32_t sensor_reading;

// Multi-line scoped type — should be flagged
std::shared_ptr<MyClass> my_ptr;

// Range-for — should NOT be flagged
void loop() {
  std::vector<int> items{};
  for (const auto &item : items) {
  }
  for (auto &x : items) {
  }
  for (int i = 0; i < 10; ++i) {
  }
}

// Structured bindings — should NOT be flagged
void bindings() { auto [x, y] = std::make_pair(1, 2); }

// Extern — should NOT be flagged
extern int ext_var;
extern std::string ext_str;

// Forward declarations — should NOT be flagged
class ForwardClass;
struct ForwardStruct;

// Correctly initialized — should NOT be flagged
int ok1 = 0;
float ok2{};
int *ok3 = nullptr;
std::vector<int> ok4{};
std::string ok5{};

// Preprocessor/macros — should NOT be flagged
#define MY_MACRO(x) int x
#define MULTI_LINE_MACRO(x) int x = 0

// Return statements — should NOT be flagged
int get_val() { return 42; }

// Expressions/assignments — should NOT be flagged
void exprs() {
  int a = 0;
  a = 5;
  int b = a + 1;
}

// new/delete — should NOT be flagged
void alloc() {
  auto *p = new int(5);
  delete p;
}

// Labels — should NOT be flagged
void jumps() {
  goto done;
done:
  return;
}

// Typedef/using — should NOT be flagged
typedef int MyInt;
using MyFloat = float;
typedef void (*Callback)(int);

// Inline functions — should NOT be flagged
inline int helper() { return 0; }
static inline void noop() {}

// Template declarations — should NOT be flagged
template <typename T> T identity(T val) { return val; }

// Enum definitions — should NOT be flagged
enum Color { RED, GREEN, BLUE };
enum class Fruit { APPLE, BANANA };

// Static member definitions — should NOT be flagged
int MyClass::static_member = 0;

// Catch blocks — should NOT be flagged
void tryCatch() {
  try {
    throw 1;
  } catch (std::exception e) {
    // e is initialized by the catch mechanism
  }
}

// Multiplication expressions — should NOT be flagged
void math() {
  int width = 10;
  int height = 20;
  int channels = 3;
  int total = width * height * channels;
  size_t rgb_size = rect_out_width * rect_out_height * kNumChannelsRgb;
}

// Multi-line expressions with array access — should NOT be flagged
void matrix_math() {
  float x0 = 1.0f;
  float y0 = 2.0f;
  float z0 = 3.0f;
  float projection_matrix_inv[3][3]{};
  const float x1 = x0 * projection_matrix_inv[0][0] +
                   y0 * projection_matrix_inv[0][1] +
                   z0 * projection_matrix_inv[0][2];
  const float y1 = x0 * projection_matrix_inv[1][0] +
                   y0 * projection_matrix_inv[1][1] +
                   z0 * projection_matrix_inv[1][2];
}

// Bitwise / arithmetic expressions — should NOT be flagged
void bitwise() {
  int a = 0;
  int b = 1;
  int c = a | b;
  int d = a ^ b;
  int e = a << 2;
  int f = a >> 1;
  int g = a + b;
  int h = a - b;
  int j = a / b;
  int k = a % b;
}

// Ternary expressions — should NOT be flagged
void ternary() {
  int a = 0;
  int b = a ? 1 : 0;
}
