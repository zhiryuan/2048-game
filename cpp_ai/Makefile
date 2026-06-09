CXX := clang++
CXXFLAGS := -std=c++17 -O3 -march=native -flto \
            -Wall -Wextra -Wno-unused-parameter
LDFLAGS := -flto

TARGET := 2048_ai
SRC := main.cpp
OBJ := main.o
HDR := types.hpp board.hpp ntuple.hpp

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CXX) $(LDFLAGS) -o $@ $^ -lpthread

$(OBJ): $(SRC) $(HDR)
	$(CXX) $(CXXFLAGS) -c $(SRC) -o $(OBJ)

clean:
	rm -f $(TARGET) $(OBJ)
