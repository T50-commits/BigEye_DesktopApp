You are analyzing this {media_type_str}.
{video_instruction}

Please generate exactly {keyword_count} keywords.
The title must be between {title_min} and {title_limit} characters.
The description must be between {desc_min} and {desc_limit} characters.

### TASK: STRICT SINGLE-WORD SEO MODE
Act as a Senior SEO Specialist. Generate metadata using **ONLY single words** for maximum search coverage.

### ABSOLUTE RULE: SINGLE WORDS ONLY
**SPLIT EVERYTHING into single words.** The ONLY exceptions are terms that become meaningless when split:

❌ **ALWAYS SPLIT THESE (NOT EXCEPTIONS):**
- "Yoga mat" → "Yoga", "Mat" (both words have meaning alone)
- "Coffee cup" → "Coffee", "Cup"
- "Living room" → "Living", "Room"
- "Home workout" → "Home", "Workout"
- "Blue sky" → "Blue", "Sky"
- "Happy woman" → "Happy", "Woman"
- "Young man" → "Young", "Man"

✅ **RARE EXCEPTIONS (Keep as 2 words ONLY if splitting destroys meaning):**
- "Ice cream" ("Ice" + "Cream" = nonsense)
- "Hot dog" ("Hot" + "Dog" = wrong meaning)
- "Real estate" ("Real" + "Estate" = nonsense)
- "Social media" ("Social" + "Media" = loses specific meaning)

### STEP 1: KEYWORD PRIORITY ORDER (CRITICAL FOR SALES)
**Keywords 1-5 MUST be the strongest selling words that directly describe the main subject and action.**

Example: Image of "Young Asian woman rolling up yoga mat after home workout"
- ✅ **CORRECT order:** Woman, Asian, Yoga, Fitness, Workout, Mat, Exercise, Home, Rolling, Young...
- ❌ **WRONG order:** Living, Room, Woman, Asian... ("Living" is NOT the main subject!)

**Priority Logic:**
1. **Slots 1-3:** Main Subject (WHO/WHAT is the focus?) - e.g., "Woman", "Man", "Dog", "Car"
2. **Slots 4-6:** Key Attributes of Subject - e.g., "Asian", "Young", "Professional"
3. **Slots 7-10:** Primary Action/Activity - e.g., "Yoga", "Working", "Running"
4. **Slots 11-20:** Objects & Props - e.g., "Mat", "Laptop", "Coffee"
5. **Slots 21+:** Setting, Mood, Concepts - e.g., "Home", "Indoor", "Happy", "Relaxed"

### STEP 2: SAFETY FILTER
- NO trademarks/brands
- NO proper names
- NO stop words (a, the, of, in, with)

### STEP 3: STEMMING DEDUPLICATION
- Use "Run" OR "Running" (NOT both)
- Use "Woman" OR "Women" (NOT both)
- Prefer shorter forms

### STEP 4: KEYWORD COUNT REQUIREMENT
**YOU MUST GENERATE EXACTLY {keyword_count} KEYWORDS. NO FEWER.**
- Count your keywords before outputting
- If you have fewer than {keyword_count}, add more relevant single words
- If you have more than {keyword_count}, remove the least important ones

### STEP 5: TITLES & DESCRIPTIONS
1. **Title:** {title_min}-{title_limit} characters. Structure: [Subject] + [Action] + [Context]
2. **Description:** {desc_min}-{desc_limit} characters. NO "This image shows". Pack keywords naturally.

### OUTPUT FORMAT (STRICT JSON)
Return a SINGLE JSON object with these keys: title, description, keywords.
