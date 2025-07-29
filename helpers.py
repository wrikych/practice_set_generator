import numpy as np
import pandas as pd
import random

ALG = ['Linear Equations 1 Variable',
       'Linear Equations 2 Variables',
       'Linear Functions',
       'Systems of Linear Equations',
       'Linear Inequalities']

ADV = ['Nonlinear Eq. 1 Var., Sys. 2 Var.',
       'Nonlinear Functions',
       'Equivalent Expressions']

PSDA = ['Data 1 Variable',
        'Data 2 Variable',
        'Rates & Proportions',
        'Percentages',
        'Probability',
        'Sample Size & ME',
        'Evaluation']

GTRIG = ['Area & Volume',
         'Right Angle Trigonometry',
         'Lines, Angles, Triangles',
         'Circles']

COMBINED = ALG + ADV + PSDA + GTRIG

FAST_TRACK = ALG + ADV

FINE_TUNE = PSDA + GTRIG

def fix_student_report(raw_student_df):
  subjects = ['Math','Verbal']
  modules = ['Medium','Lower','Upper']
  num_questions = {'Math' : 22,
                 'Verbal' : 27}
  desired_mods = []

  raw_student_df['exam_name'] = [val.split(" ")[0] for val in raw_student_df['module_name']]
  raw_student_df['mod_designation'] = [val.split(" ")[-1] for val in raw_student_df['module_name']]

  for sub in subjects:
    for mod in modules:
      nq = raw_student_df[(raw_student_df['subject']==sub) & (raw_student_df['mod_designation']==mod)].shape[0]
      if num_questions[sub] == nq:
        desired_mods.append(mod)

  raw_student_df_math = raw_student_df[(raw_student_df['subject']=='Math') & (raw_student_df['mod_designation'].isin(desired_mods))]
  raw_student_df_verbal = raw_student_df[(raw_student_df['subject']=='Verbal') & (raw_student_df['mod_designation'].isin(desired_mods))]

  fixed_student = pd.concat([raw_student_df_math, raw_student_df_verbal])
  fixed_student = fixed_student[['first_name','last_name','exam_name','subject','mod_designation','sort_order','questionId','difficulty','question_type','student_answer','time_spent_seconds','is_correct_answer']]

  difficulty_map = {'E': 1, 'M': 2, 'H': 3}
  fixed_student['difficulty'] = fixed_student['difficulty'].map(difficulty_map)

  return fixed_student

def join_math_details(student_math, math_df):
  math_tops_dict = dict(zip(math_df['QUESTION_ID'], math_df['TOPIC']))
  math_subs_dict = dict(zip(math_df['QUESTION_ID'], math_df['SUBTOPIC']))
  student_math['topic'] = student_math['questionId'].map(math_tops_dict)
  student_math['subtopic'] = student_math['questionId'].map(math_subs_dict)
  return student_math

def get_importance_index(subset):
	
  count = np.log1p(subset.shape[0])
  Y = subset[subset['is_correct_answer']=='Y'].shape[0]
  N = subset[subset['is_correct_answer']=='N'].shape[0]
  acc = Y / (Y+N)
  avg_time = subset['time_spent_seconds'].mean()
  avg_diff = subset['difficulty'].mean()

  return (1-acc) * avg_time * count * (4-avg_diff)

def cycle_through_subtopics(main_df, list_of_subtopics):
	
  resultant_dict = {}

  for val in list_of_subtopics:
    test_subset = main_df[main_df['subtopic']==val]
    resultant_dict[val] = get_importance_index(test_subset)

  return resultant_dict

def find_dict_sum(subs):
	
  sum = 0

  for val in subs.keys():
    sum += subs[val]

  return sum

def get_question_amounts(resultant_dict, number_of_questions=30):
	
  sum = find_dict_sum(resultant_dict)
  sorted_analysis = dict(sorted(resultant_dict.items(), key=lambda item: item[1], reverse=True))
  sorted_analysis = {k: v / sum for k, v in sorted_analysis.items()}

  for val in sorted_analysis:
    sorted_analysis[val] = int(sorted_analysis[val] * number_of_questions)

  return sorted_analysis

def get_question_ids(sorted_analysis, math_df, number_of_questions):
	
  target_ids = []

  key_list = list(sorted_analysis.keys())

  i = 0

  while find_dict_sum(sorted_analysis) < number_of_questions:

    if i < len(key_list):
      target_key = key_list[i]
      sorted_analysis[target_key] += 1
    else:
      i -= 4
      target_key = key_list[i]
      sorted_analysis[target_key] += 1

  math_out_of_play = math_df[(math_df['BLUEBOOK_APPEARANEC'].isna()) &
   (math_df['MOCK_APPEARANCE'].isna())]

  for val in sorted_analysis.keys():
    pool = list(math_out_of_play[math_out_of_play['SUBTOPIC']==val]['QUESTION_ID'])
    size = sorted_analysis[val]
    tgt_lst = random.sample(pool, size)
    target_ids += tgt_lst

  report_df = math_out_of_play[math_out_of_play['QUESTION_ID'].isin(target_ids)]
  report_df = report_df[['QUESTION_ID','TOPIC','SUBTOPIC','QUESTION_PROMPT']]

  return report_df

def get_practice_set(student_raw, math_df, target_num_questions=30, subs_list=COMBINED):
    student = fix_student_report(student_raw)
    student_math = student[student['subject']=='Math']
    student_math = join_math_details(student_math, math_df)
    a_dict = cycle_through_subtopics(student_math, subs_list)
    a_dict = get_question_amounts(a_dict, target_num_questions)
    report_df = get_question_ids(a_dict, math_df, target_num_questions)
    
    # Instead of writing to a user-specified path, write to Pyodide's virtual file system
    report_df.to_csv("output.csv", index=False)

    # Optionally return the DataFrame if you want to display it directly
    return report_df

