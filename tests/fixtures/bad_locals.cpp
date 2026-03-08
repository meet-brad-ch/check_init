// Each line should be flagged as uninitialized
void func() {
  int a;            // uninitialized int
  float b;          // uninitialized float
  bool c;           // uninitialized bool
  int *p;           // uninitialized pointer
  uint8_t byte;     // uninitialized uint8_t
  double d;         // uninitialized double
  char ch;          // uninitialized char
  const int *cp;    // uninitialized const pointer
  unsigned long ul; // multi-word type
  long long ll;     // multi-word type
  int16_t val;      // fixed-width type
  size_t sz;        // size_t
  int32_t sensor;   // int32_t
  uint64_t counter; // uint64_t
  volatile int vi;  // volatile qualified
  static float sf;  // static local
  signed char sc;   // signed char
  unsigned int ui;  // unsigned int
  ptrdiff_t diff;   // ptrdiff_t
}
