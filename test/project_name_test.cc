#include <gtest/gtest.h>
#include <project_name/project_name.h>

namespace {

TEST(ProjectName, AnswerReturnsExpectedValue) {
  EXPECT_EQ(project_name::Answer(), 42);
}

}  // namespace
