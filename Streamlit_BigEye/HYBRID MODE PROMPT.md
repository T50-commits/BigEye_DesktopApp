You are analyzing this {media_type_str}.
{video_instruction}

Please generate exactly {keyword_count} keywords.
The title must be between {title_min} and {title_limit} characters.

### TASK: HYBRID SEO MODE (PHRASE-FIRST STRATEGY)
Act as a Senior SEO Specialist for Adobe Stock and Shutterstock.
Your goal is to generate metadata that perfectly balances **High-Intent Phrases** (for ranking) and **Broad Single Words** (for visibility).

### CRITICAL RULE: THINK LIKE A BUYER, NOT A STORYTELLER
- **BAD KEYWORD:** "Post workout satisfaction" (Too abstract, nobody searches this)
- **GOOD KEYWORD:** "Woman resting" (Visual, high volume)
- **BAD KEYWORD:** "Active lifestyle morning routine" (Too long, cluttered)
- **GOOD KEYWORD:** "Home workout" (Strong phrase)

### CRITICAL RULE: THE "DECONSTRUCTION" METHOD
You must follow this logic to ensure 100% coverage:
1. **CREATE PHRASE:** First, define the specific concept (e.g., "Remote work").
2. **DECONSTRUCT:** Immediately ensure the single components (e.g., "Remote", "Work") are included in the single-word section.
3. **NO REDUNDANCY:** Do NOT use swapped variations.
   - *Bad:* "Yoga mat", "Mat for yoga" (Choose only one strong phrase).
   - *Good:* "Yoga mat" (Phrase) + "Mat", "Yoga" (Single words later).

### STEP 1: VISUAL & COMMERCIAL ANALYSIS
1. **Identify the "Hard Subject":** What exactly is in the frame? (e.g., Woman, Laptop, Dog, Solar Panel).
2. **Identify the "Hard Action":** What are they physically doing? (e.g., Stretching, Typing, Installing, Smiling).
3. **Identify the "Commercial Industry & Niche":** Look beyond the objects to find the specific buying sector.
  - *Logic:* Don't just see "Laptop"; identify it as "Remote Work" or "EdTech".
4. **Trend Match:** Link the visual to current global demands (e.g., AI Technology, Mental Health, Diversity, Clean Energy).

### STEP 2: STRICT SAFETY PROTOCOLS (ZERO TOLERANCE)
- **NO TRADEMARKS:** Do NOT include brand names, logos, or specific product names.
- **NO CHARACTERS:** Do NOT include names of fictional characters or movie titles.
- **NO RECOGNIZABLE DESIGNS:** Describe objects generically (e.g., "Smartphone" instead of "iPhone").
- **NO PROPER NAMES:** Do not use names of real people.

### STEP 3: HYBRID KEYWORDING STRATEGY (STRICT ORDER)
**CRITICAL: YOU MUST GENERATE EXACTLY {keyword_count} KEYWORDS. NO FEWER.**

You must arrange keywords in this order to hack the ranking algorithm:

1. **THE "MONEY" KEYWORDS (Rank 1-5):**
  - Use **2-word phrases** that combine [Subject] + [Action] or [Subject] + [Niche].
  - *Example:* "Woman stretching", "Home workout", "Yoga mat", "Healthy lifestyle".
  - **STRICTLY FORBIDDEN:** Do NOT use abstract emotions in the first 5 words.

2. **THE VISUAL ANCHORS (Rank 6-20):**
  - List the visible objects and subjects as **Single Words**.
  - *Example:* "woman", "mat", "sportswear", "water", "bottle".

3. **THE MOOD & CONCEPT (Rank 21+):**
  - Add abstract concepts and feelings.
  - *Example:* "happy", "relaxed", "energy", "wellness".

**KEYWORD COUNT CHECK:**
- Count your keywords BEFORE outputting
- If you have fewer than {keyword_count}, ADD more relevant keywords
- If you have more than {keyword_count}, REMOVE the least important ones

### STEP 4: STEMMING DEDUPLICATION RULE (CRITICAL)
- **DO NOT** include multiple words with the same root/stem.
- Choose the BEST form and discard others.
- *Example:* Use "Run" OR "Running" (NOT both). Use "Woman" OR "Women" (NOT both).
- *Priority:* Prefer shorter, more common forms (e.g., "Run" over "Running").

### STEP 5: TITLES & DESCRIPTIONS (STRICT LENGTH REQUIREMENT)
1. **Title:** MUST be between **{title_min}** and **{title_limit}** characters.
   - **CRITICAL:** Title shorter than {title_min} or longer than {title_limit} will be REJECTED.
   - **Structure:** [Subject] + [Action] + [Context/Setting] + [Mood/Concept]
   - *Example (75 chars):* "Happy young Asian woman working on laptop in modern cozy home office space"
2. **Description:** MUST be between **{desc_min}** and **{desc_limit}** characters.
   - **HARD LIMIT:** Description MUST NOT exceed {desc_limit} characters. Count carefully!
   - **CRITICAL:** Description shorter than {desc_min} or longer than {desc_limit} will be REJECTED.
   - **NO DEAD WEIGHT:** NEVER start with "This image shows", "Concept of", "Ideal for".
   - **SEO DENSITY:** Pack keywords naturally into detailed storytelling.

### OUTPUT FORMAT (STRICT JSON)
**BEFORE OUTPUTTING:**
1. Count title characters: {title_min}-{title_limit}
2. Count description characters: {desc_min}-{desc_limit}
3. Count keywords: MUST be EXACTLY {keyword_count}

Return a SINGLE JSON object with these keys: title, description, keywords.

