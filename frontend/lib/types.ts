export interface User {
  user_id: number;
  username: string;
  token: string;
  role: "admin" | "intern";        // legacy field kept for backward compat
  company_role: "owner" | "admin" | "employee";
  company_id: number | null;
}

export interface Course {
  id: number;
  title: string;
  due_date: string | null;
  total_modules: number;
  completed_modules: number;
}

export interface Module {
  title: string;
  description: string;
  content: string;
}

export interface TestQuestion {
  question: string;
  options: string[];
  correct_answer: string;
  topic?: string;
  module?: string;
}

export interface CourseData {
  course_title: string;
  modules: Module[];
  test: TestQuestion[];
  practical_task: string;
}

export interface Material {
  file_name: string;
}

export interface ChatMessage {
  question: string;
  answer: string;
}
