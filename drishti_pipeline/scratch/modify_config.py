import re

with open('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_pipeline/config.py', 'r') as f:
    code = f.read()

# Define extra symptoms to inject into pools based on differential_candidates / condition_tag
# We'll do this by finding each symptom_pool block and checking the surrounding context for keywords.

def add_symptoms(match):
    context = match.group(0)
    
    # Extract existing symptoms
    pool_str = match.group(1)
    
    # We will build a set of new symptoms to append
    new_symptoms = []
    
    # Heuristics based on context
    context_lower = context.lower()
    
    if "fatigue" not in pool_str:
        if any(x in context_lower for x in ["obesity", "e11", "e66", "metabolic", "d50", "e05.9", "anemia", "hyperthyroid", "fever", "dengue", "malaria", "typhoid", "chikungunya", "viral"]):
            new_symptoms.append('("fatigue", "nonspecific")')
    
    if "headache" not in pool_str and "severe headache" not in pool_str:
        if any(x in context_lower for x in ["hypertens", "i10", "dengue", "anxiety", "apnoea"]):
            new_symptoms.append('("headache", "supportive")')
            
    if "abdominal pain" not in pool_str:
        if any(x in context_lower for x in ["gastro", "a09", "typhoid", "dengue", "malaria"]):
            new_symptoms.append('("abdominal pain", "supportive")')
            
    if "nausea" not in pool_str:
        if any(x in context_lower for x in ["gastro", "typhoid", "dengue", "migraine"]):
            new_symptoms.append('("nausea", "supportive")')
            
    if "dizziness" not in pool_str:
        if any(x in context_lower for x in ["hypertens", "i10", "failure", "anemia", "anxiety"]):
            new_symptoms.append('("dizziness", "supportive")')
            
    if "breathlessness" not in pool_str and "severe breathlessness" not in pool_str:
        if any(x in context_lower for x in ["respiratory", "j96", "failure", "anemia"]):
            new_symptoms.append('("breathlessness", "supportive")')
            
    if "joint pain" not in pool_str and "severe joint pain" not in pool_str:
        if any(x in context_lower for x in ["chikungunya", "obesity", "osteoarthritis"]):
            new_symptoms.append('("joint pain", "supportive")')
            
    if "sweating" not in pool_str:
        if any(x in context_lower for x in ["anxiety", "hyperthyroid", "malaria"]):
            new_symptoms.append('("sweating", "supportive")')
            
    if "loss of appetite" not in pool_str:
        if any(x in context_lower for x in ["fever", "gastro", "typhoid", "tuberculosis", "anemia"]):
            new_symptoms.append('("loss of appetite", "nonspecific")')
            
    if "muscle ache" not in pool_str and "body ache" not in pool_str:
        if any(x in context_lower for x in ["dengue", "chikungunya", "viral", "fever"]):
            new_symptoms.append('("muscle ache", "supportive")')

    if "palpitations" not in pool_str:
        if any(x in context_lower for x in ["failure", "anxiety", "hyperthyroid"]):
            new_symptoms.append('("palpitations", "supportive")')
            
    # Add some generic nonspecifics to pad the pools to 5-8
    generics = ['("general weakness", "nonspecific")', '("poor sleep", "nonspecific")', '("mild discomfort", "nonspecific")']
    for g in generics:
        if g not in pool_str and g not in new_symptoms:
            new_symptoms.append(g)

    # Reconstruct the pool
    if new_symptoms:
        # We need to insert these before the closing bracket of the pool
        insertion = ",\n            " + ",\n            ".join(new_symptoms)
        
        # Check if the pool already has a trailing comma
        if pool_str.strip().endswith(","):
            new_pool_str = pool_str.rstrip() + insertion + ","
        else:
            new_pool_str = pool_str + insertion + ","
            
        return context.replace(pool_str, new_pool_str)
    return context

# We want to match the whole dictionary block for a condition to have context
pattern = re.compile(r'(\"symptom_pool\": \[\s*(?:[^\]]+)\s*\])', re.MULTILINE)
# But wait, context should be the whole entry!
# Let's match from { up to } and apply the replacement inside.
def process_entry(match):
    entry_str = match.group(0)
    return re.sub(r'\"symptom_pool\": \[\s*([\s\S]*?)\s*\]', lambda m: add_symptoms_to_pool(m, entry_str), entry_str)

def add_symptoms_to_pool(m, context):
    pool_str = m.group(1)
    new_symptoms = []
    c = context.lower()
    
    # SAME LOGIC AS ABOVE
    if "fatigue" not in pool_str:
        if any(x in c for x in ["obesity", "e11", "e66", "metabolic", "d50", "e05.9", "anemia", "hyperthyroid", "fever", "dengue", "malaria", "typhoid", "chikungunya", "viral"]):
            new_symptoms.append('("fatigue", "nonspecific")')
    if "headache" not in pool_str and "severe headache" not in pool_str:
        if any(x in c for x in ["hypertens", "i10", "dengue", "anxiety", "apnoea"]):
            new_symptoms.append('("headache", "supportive")')
    if "abdominal pain" not in pool_str and "lower abdominal pain" not in pool_str:
        if any(x in c for x in ["gastro", "a09", "typhoid", "dengue", "malaria"]):
            new_symptoms.append('("abdominal pain", "supportive")')
    if "nausea" not in pool_str:
        if any(x in c for x in ["gastro", "typhoid", "dengue", "migraine"]):
            new_symptoms.append('("nausea", "supportive")')
    if "dizziness" not in pool_str:
        if any(x in c for x in ["hypertens", "i10", "failure", "anemia", "anxiety"]):
            new_symptoms.append('("dizziness", "supportive")')
    if "breathlessness" not in pool_str and "severe breathlessness" not in pool_str:
        if any(x in c for x in ["respiratory", "j96", "failure", "anemia"]):
            new_symptoms.append('("breathlessness", "supportive")')
    if "joint pain" not in pool_str and "severe joint pain" not in pool_str:
        if any(x in c for x in ["chikungunya", "obesity", "osteoarthritis"]):
            new_symptoms.append('("joint pain", "supportive")')
    if "sweating" not in pool_str:
        if any(x in c for x in ["anxiety", "hyperthyroid", "malaria"]):
            new_symptoms.append('("sweating", "supportive")')
    if "loss of appetite" not in pool_str:
        if any(x in c for x in ["fever", "gastro", "typhoid", "tuberculosis", "anemia"]):
            new_symptoms.append('("loss of appetite", "nonspecific")')
    if "muscle ache" not in pool_str and "body ache" not in pool_str:
        if any(x in c for x in ["dengue", "chikungunya", "viral", "fever", "malaria"]):
            new_symptoms.append('("muscle ache", "supportive")')
    if "palpitations" not in pool_str:
        if any(x in c for x in ["failure", "anxiety", "hyperthyroid"]):
            new_symptoms.append('("palpitations", "supportive")')

    generics = ['("general weakness", "nonspecific")', '("poor sleep", "nonspecific")', '("mild discomfort", "nonspecific")']
    for g in generics:
        if g not in pool_str and g not in new_symptoms:
            new_symptoms.append(g)

    # ensure size is 5-8
    # count existing
    existing_count = len([x for x in pool_str.split('\n') if '(' in x])
    # truncate new_symptoms if it exceeds 8 total
    max_to_add = max(0, 8 - existing_count)
    new_symptoms = new_symptoms[:max_to_add]

    if not new_symptoms:
        return m.group(0)

    insertion = ",\n            " + ",\n            ".join(new_symptoms)
    if pool_str.strip().endswith(","):
        return f'"symptom_pool": [\n{pool_str.rstrip()}{insertion},\n        ]'
    else:
        return f'"symptom_pool": [\n{pool_str}{insertion},\n        ]'

# regex to find dictionaries that have "symptom_pool"
# This might be tricky because dictionaries are nested.
# Let's split by "symptom_pool\": [" and modify them one by one.
import ast

def process_file(file_content):
    parts = file_content.split('"symptom_pool": [')
    if len(parts) == 1:
        return file_content
    
    new_content = parts[0]
    for i in range(1, len(parts)):
        prev_part = new_content
        curr_part = parts[i]
        
        # Context is the last 500 chars of prev_part
        context = prev_part[-500:].lower()
        
        # The pool string ends at the first ']'
        end_idx = curr_part.find(']')
        pool_str = curr_part[:end_idx]
        remainder = curr_part[end_idx:]
        
        new_symptoms = []
        if "fatigue" not in pool_str:
            if any(x in context for x in ["obesity", "e11", "e66", "metabolic", "d50", "e05.9", "anemia", "hyperthyroid", "fever", "dengue", "malaria", "typhoid", "chikungunya", "viral", "a90", "a91", "a92.0", "a01.0"]):
                new_symptoms.append('("fatigue", "nonspecific")')
        if "headache" not in pool_str and "severe headache" not in pool_str:
            if any(x in context for x in ["hypertens", "i10", "dengue", "anxiety", "apnoea", "a90", "a91"]):
                new_symptoms.append('("headache", "supportive")')
        if "abdominal pain" not in pool_str and "lower abdominal pain" not in pool_str:
            if any(x in context for x in ["gastro", "a09", "typhoid", "dengue", "malaria", "a01.0", "a90", "a91"]):
                new_symptoms.append('("abdominal pain", "supportive")')
        if "nausea" not in pool_str:
            if any(x in context for x in ["gastro", "typhoid", "dengue", "migraine", "a09", "a01.0", "a90", "a91"]):
                new_symptoms.append('("nausea", "supportive")')
        if "dizziness" not in pool_str:
            if any(x in context for x in ["hypertens", "i10", "failure", "anemia", "anxiety", "d50", "f41.0"]):
                new_symptoms.append('("dizziness", "supportive")')
        if "breathlessness" not in pool_str and "severe breathlessness" not in pool_str:
            if any(x in context for x in ["respiratory", "j96", "failure", "anemia", "d50"]):
                new_symptoms.append('("breathlessness", "supportive")')
        if "joint pain" not in pool_str and "severe joint pain" not in pool_str:
            if any(x in context for x in ["chikungunya", "obesity", "osteoarthritis", "a92.0"]):
                new_symptoms.append('("joint pain", "supportive")')
        if "sweating" not in pool_str:
            if any(x in context for x in ["anxiety", "hyperthyroid", "malaria", "f41.0", "e05.9", "b54"]):
                new_symptoms.append('("sweating", "supportive")')
        if "loss of appetite" not in pool_str:
            if any(x in context for x in ["fever", "gastro", "typhoid", "tuberculosis", "anemia", "a01.0", "a90", "a91", "a15", "d50"]):
                new_symptoms.append('("loss of appetite", "nonspecific")')
        if "muscle ache" not in pool_str and "body ache" not in pool_str:
            if any(x in context for x in ["dengue", "chikungunya", "viral", "fever", "malaria", "a90", "a91", "a92.0", "b54"]):
                new_symptoms.append('("muscle ache", "supportive")')
        if "palpitations" not in pool_str:
            if any(x in context for x in ["failure", "anxiety", "hyperthyroid", "f41.0", "e05.9"]):
                new_symptoms.append('("palpitations", "supportive")')
                
        generics = ['("general weakness", "nonspecific")', '("poor sleep", "nonspecific")', '("mild discomfort", "nonspecific")']
        for g in generics:
            if g not in pool_str and g not in new_symptoms:
                new_symptoms.append(g)

        existing_count = len([x for x in pool_str.split('\n') if '(' in x])
        max_to_add = max(0, 8 - existing_count)
        new_symptoms = new_symptoms[:max_to_add]

        if new_symptoms:
            insertion = ",\n            " + ",\n            ".join(new_symptoms)
            if pool_str.strip().endswith(","):
                new_pool = pool_str.rstrip() + insertion + ",\n        "
            else:
                new_pool = pool_str + insertion + ",\n        "
        else:
            new_pool = pool_str
            
        new_content += '"symptom_pool": [' + new_pool + remainder

    return new_content

with open('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_pipeline/config.py', 'w') as f:
    f.write(process_file(code))

print("Modified config.py")
