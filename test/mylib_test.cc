#include <gtest/gtest.h>
#include <mylib/mylib.h>

namespace {

TEST(AnswerTest, ReturnsExpectedValue) { EXPECT_EQ(mylib::Answer(), 42); }

}  // namespace
