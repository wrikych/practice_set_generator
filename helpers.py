import numpy as np
import pandas as pd

# Define your constants first
ALG = [
    'Linear Equations 1 Variable',
    'Linear Equations 2 Variables',
    'Linear Functions',
    'Systems of Linear Equations',
    'Linear Inequalities'
]

ADV = [
    'Nonlinear Eq. 1 Var., Sys. 2 Var.',
    'Nonlinear Functions',
    'Equivalent Expressions'
]

PSDA = [
    'Data 1 Variable',
    'Data 2 Variable',
    'Rates & Proportions',
    'Percentages',
    'Probability',
    'Sample Size & ME',
    'Evaluation'
]

GTRIG = [
    'Area & Volume',
    'Right Angle Trigonometry',
    'Lines, Angles, Triangles',
    'Circles'
]

COMBINED = ALG + ADV + PSDA + GTRIG
FAST_TRACK = ALG + ADV
FINE_TUNE = PSDA + GTRIG

def fix_student_report(raw_student_df):
    try:
        # Keep original column names case-sensitive
        required_columns = ['module_name', 'subject', 'first_name', 'last_name', 
                          'sort_order', 'questionId', 'difficulty', 'question_type',
                          'student_answer', 'time_spent_seconds', 'is_correct_answer']
        
        missing_cols = [col for col in required_columns if col not in raw_student_df.columns]
        if missing_cols:
            raise ValueError(f"CSV missing required columns: {missing_cols}")
            
        subjects = ['Math','Verbal']
        modules = ['Medium','Lower','Upper']
        num_questions = {'Math': 22, 'Verbal': 27}
        desired_mods = []

        # Safely split module names
        raw_student_df['exam_name'] = raw_student_df['module_name'].str.split().str[0]
        raw_student_df['mod_designation'] = raw_student_df['module_name'].str.split().str[-1]

        for sub in subjects:
            for mod in modules:
                nq = raw_student_df[
                    (raw_student_df['subject'] == sub) & 
                    (raw_student_df['mod_designation'] == mod)
                ].shape[0]
                if num_questions[sub] == nq:
                    desired_mods.append(mod)

        raw_student_df_math = raw_student_df[
            (raw_student_df['subject'] == 'Math') & 
            (raw_student_df['mod_designation'].isin(desired_mods))
        ]
        
        raw_student_df_verbal = raw_student_df[
            (raw_student_df['subject'] == 'Verbal') & 
            (raw_student_df['mod_designation'].isin(desired_mods))
        ]

        fixed_student = pd.concat([raw_student_df_math, raw_student_df_verbal])
        
        # Select columns with exact case-sensitive names
        fixed_student = fixed_student[[
            'first_name', 'last_name', 'exam_name', 'subject', 
            'mod_designation', 'sort_order', 'questionId', 
            'difficulty', 'question_type', 'student_answer', 
            'time_spent_seconds', 'is_correct_answer'
        ]]

        # Map difficulty safely
        difficulty_map = {'E': 1, 'M': 2, 'H': 3}
        fixed_student['difficulty'] = fixed_student['difficulty'].map(difficulty_map).fillna(2)  # Default to medium

        return fixed_student
        
    except Exception as e:
        print(f"Error in fix_student_report: {str(e)}")
        raise

def join_math_details(student_math, math_df):
    try:
        # Keep original case-sensitive column names
        required_math_cols = ['QUESTION_ID', 'TOPIC', 'SUBTOPIC']
        missing_cols = [col for col in required_math_cols if col not in math_df.columns]
        if missing_cols:
            raise ValueError(f"Math CSV missing required columns: {missing_cols}")
            
        math_tops_dict = dict(zip(math_df['QUESTION_ID'], math_df['TOPIC']))
        math_subs_dict = dict(zip(math_df['QUESTION_ID'], math_df['SUBTOPIC']))
        
        student_math['topic'] = student_math['questionId'].map(math_tops_dict)
        student_math['subtopic'] = student_math['questionId'].map(math_subs_dict)
        
        return student_math
    except Exception as e:
        print(f"Error in join_math_details: {str(e)}")
        raise

def get_importance_index(subset):
    try:
        count = np.log1p(subset.shape[0])
        
        # Handle case where is_correct_answer might have different values
        subset['is_correct_answer'] = subset['is_correct_answer'].astype(str).str.upper().str.strip()
        
        Y = subset[subset['is_correct_answer'] == 'Y'].shape[0]
        N = subset[subset['is_correct_answer'] == 'N'].shape[0]
        
        if (Y + N) == 0:
            return 0
            
        acc = Y / (Y + N)
        avg_time = subset['time_spent_seconds'].mean()
        avg_diff = subset['difficulty'].mean()

        return (1 - acc) * avg_time * count * (4 - avg_diff)
    except Exception as e:
        print(f"Error in get_importance_index: {str(e)}")
        return 0

def cycle_through_subtopics(main_df, list_of_subtopics):
    resultant_dict = {}
    
    for val in list_of_subtopics:
        try:
            test_subset = main_df[main_df['subtopic'] == val]
            if not test_subset.empty:
                resultant_dict[val] = get_importance_index(test_subset)
        except:
            continue
            
    return resultant_dict

def find_dict_sum(subs):
    return sum(subs.values()) if subs else 0

def get_question_amounts(resultant_dict, number_of_questions=30):
    try:
        total = find_dict_sum(resultant_dict)
        if total == 0:
            return {k: 1 for k in resultant_dict.keys()}  # Default equal distribution
            
        sorted_analysis = dict(sorted(resultant_dict.items(), key=lambda item: item[1], reverse=True))
        sorted_analysis = {k: (v / total) * number_of_questions for k, v in sorted_analysis.items()}
        
        # Round to integers
        sorted_analysis = {k: max(1, int(round(v))) for k, v in sorted_analysis.items()}
        
        # Adjust total if needed
        current_total = sum(sorted_analysis.values())
        if current_total < number_of_questions:
            # Add remaining questions to the top category
            top_key = next(iter(sorted_analysis))
            sorted_analysis[top_key] += number_of_questions - current_total
            
        return sorted_analysis
    except Exception as e:
        print(f"Error in get_question_amounts: {str(e)}")
        return {}

def get_question_ids(sorted_analysis, math_df, number_of_questions):
    try:
        target_ids = []
        key_list = list(sorted_analysis.keys())
        
        # Get questions not in bluebook or mock (using exact column names)
        math_out_of_play = math_df[
            (pd.isna(math_df['BLUEBOOK_APPEARANEC'])) & 
            (pd.isna(math_df['MOCK_APPEARANCE']))
        ]
        
        for val in sorted_analysis.keys():
            pool = list(math_out_of_play[
                math_out_of_play['SUBTOPIC'] == val
            ]['QUESTION_ID'])
            
            if not pool:
                continue
                
            size = min(sorted_analysis[val], len(pool))
            if size <= 0:
                continue
                
            # Use pandas sample instead of random.sample for Pyodide compatibility
            selected = math_out_of_play[
                math_out_of_play['SUBTOPIC'] == val
            ].sample(n=size, replace=False)['QUESTION_ID'].tolist()
            
            target_ids.extend(selected)
        
        report_df = math_out_of_play[
            math_out_of_play['QUESTION_ID'].isin(target_ids)
        ][['QUESTION_ID', 'TOPIC', 'SUBTOPIC', 'QUESTION_PROMPT']]
        
        return report_df
    except Exception as e:
        print(f"Error in get_question_ids: {str(e)}")
        return pd.DataFrame()

def get_practice_set(student_raw, math_df, target_num_questions=30, subs_list=COMBINED):
    try:
        print("Starting get_practice_set...")
        student = fix_student_report(student_raw)
        print("Fixed student report")
        
        student_math = student[student['subject'] == 'Math']
        print(f"Filtered math questions: {len(student_math)}")
        
        student_math = join_math_details(student_math, math_df)
        print("Joined math details")
        
        a_dict = cycle_through_subtopics(student_math, subs_list)
        print(f"Subtopics analysis: {a_dict}")
        
        a_dict = get_question_amounts(a_dict, target_num_questions)
        print(f"Question amounts: {a_dict}")
        
        report_df = get_question_ids(a_dict, math_df, target_num_questions)
        print(f"Generated report with {len(report_df)} questions")
        
        # Ensure output.csv is written
        report_df.to_csv("output.csv", index=False)
        print("Successfully wrote output.csv")
        
        return report_df
    except Exception as e:
        print(f"Error in get_practice_set: {str(e)}")
        raise