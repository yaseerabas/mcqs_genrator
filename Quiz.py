import streamlit as st
import google.generativeai as genai
import json
import re

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("Google API Key not found in Streamlit secrets. Please ensure it's set in .streamlit/secrets.toml as GOOGLE_API_KEY.")
    st.stop()

def generate_quiz(topic, num_questions):
    prompt = f"""
    Generate a multiple-choice quiz on the topic of "{topic}".
    The quiz should have {num_questions} questions.
    Each question should have 4 options (A, B, C, D) and specify the correct answer and a brief explanation.
    Provide the output strictly in a JSON format like this, wrapped in markdown code block fences:
    ```json
    {{
      "quiz": [
        {{
          "question": "Question 1 text?",
          "options": {{
            "A": "Option A text",
            "B": "Option B text",
            "C": "Option C text",
            "D": "Option D text"
          }},
          "answer": "A",
          "explanation": "Explanation for why A is correct."
        }},
        {{
          "question": "Question 2 text?",
          "options": {{
            "A": "Option A text",
            "B": "Option B text",
            "C": "Option C text",
            "D": "Option D text"
          }},
          "answer": "B",
          "explanation": "Explanation for why B is correct."
        }}
      ]
    }}
    ```
    Do not include any other text or conversational elements outside the JSON code block.
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash') 

    try:
        response = model.generate_content(prompt)
        raw_text = response.text

        match = re.search(r"```json\s*(\{.*\})\s*```", raw_text, re.DOTALL)
        
        json_string = None
        if match:
            json_string = match.group(1)
        else:
            st.warning("Regex did not find expected JSON block. Attempting fallback cleaning.")
            json_string = raw_text.replace("```json", "").replace("```", "").strip()
            
        if not json_string:
            st.error("Could not extract any JSON content from the response.")
            return None

        if not json_string.strip():
            st.error("Extracted JSON string is empty or contains only whitespace. Cannot parse.")
            return None

        quiz_data = json.loads(json_string)
        return quiz_data.get("quiz", [])
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse quiz data. Error: {e}. Raw response after cleaning attempt: '{json_string}'")
        return None
    except Exception as e:
        st.error(f"An error occurred while generating the quiz: {e}")
        return None

st.set_page_config(page_title="Quiz Generator", layout="centered")
st.title("Quiz Generator")
st.markdown("Enter a topic, and our bot will create a multiple-choice quiz for you!")

topic = st.text_input("Enter the quiz topic:")
num_questions = st.slider("Number of questions:", 1, 10, 5)

if st.button("Generate Quiz"):
    if topic:
        with st.spinner("Generating your quiz... This might take a moment."):
            quiz = generate_quiz(topic, num_questions)

        if quiz:
            st.session_state.quiz = quiz
            st.session_state.current_question_index = 0
            st.session_state.score = 0
            st.session_state.user_answers = {} 
            st.success("Quiz generated successfully!")
            st.rerun()

    else:
        st.warning("Please enter a topic to generate a quiz.")

if 'quiz' in st.session_state and st.session_state.quiz:
    st.header("Take the Quiz!")
    current_q_index = st.session_state.current_question_index
    quiz = st.session_state.quiz

    if current_q_index < len(quiz):
        question_data = quiz[current_q_index]
        st.subheader(f"Question {current_q_index + 1}/{len(quiz)}")
        st.write(question_data["question"])

        selected_key = st.session_state.user_answers.get(current_q_index)

        selected_option = st.radio(
            "Select your answer:",
            options=list(question_data["options"].keys()),
            format_func=lambda x: f"{x}. {question_data['options'][x]}",
            key=f"q_{current_q_index}",
            index=list(question_data["options"].keys()).index(selected_key) if selected_key else 0 # Set index based on previous selection
        )

        st.session_state.user_answers[current_q_index] = selected_option


        col1, col2 = st.columns(2)
        with col1:
            if st.button("Previous Question", disabled=(current_q_index == 0)):
                st.session_state.current_question_index -= 1
                st.rerun()
        with col2:
            is_last_question = (current_q_index == len(quiz) - 1)
            next_button_label = "Complete Quiz" if is_last_question else "Next Question"

            if st.button(next_button_label):
                if is_last_question:
                    st.session_state.current_question_index += 1
                    st.rerun()
                else:
                    st.session_state.current_question_index += 1
                    st.rerun()
    else:
        st.header("Quiz Completed!")
        
        score = 0
        st.session_state.score = 0 
        st.write("### Your Results:")
        
        all_answered = True
        for i, q_data in enumerate(quiz):
            user_ans = st.session_state.user_answers.get(i)
            correct_ans = q_data["answer"]

            st.markdown(f"**Question {i+1}:** {q_data['question']}")
            
            if user_ans:
                st.markdown(f"**Your Answer:** {user_ans}. {q_data['options'][user_ans]}")
                if user_ans == correct_ans:
                    st.success("Correct!")
                    score += 1
                else:
                    st.error("Incorrect!")
            else:
                st.warning("You did not answer this question.")
                all_answered = False

            st.markdown(f"**Correct Answer:** {correct_ans}. {q_data['options'][correct_ans]}")
            st.markdown(f"**Explanation:** {q_data['explanation']}")
            st.markdown("---") 

        st.session_state.score = score
        st.subheader(f"You scored {st.session_state.score} out of {len(quiz)} questions!")
        
        if not all_answered:
            st.info("Some questions were not answered. Your score reflects answered questions only.")

        if st.button("Start New Quiz"):
            for key in ["quiz", "current_question_index", "score", "user_answers"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()