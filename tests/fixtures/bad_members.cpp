// Struct/class members without initializers
struct BadStruct {
  int x;
  float *ptr;
  bool active;
  int arr[4];
  double value;
  uint32_t id;
  char name[64];
};

class BadClass {
public:
  void method() {}

private:
  int count;
  float *data;
  bool ready;
  size_t length;
  std::vector<int> items;
  std::string label;
};
