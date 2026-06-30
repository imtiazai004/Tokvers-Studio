"""Video type definitions and instructions for script and visual generation."""

VIDEO_TYPES = {
    "ugc": {
        "name": "UGC (User-Generated Content)",
        "description": "Authentic, selfie-style content that looks like a real person filming themselves on their phone",
        "script_structure": "Native hook | Casual product mention | Real opinion / why I love it | Honest result | Soft recommendation",
        "tone": "authentic, casual, unscripted, friendly, like talking to the camera",
        "pacing": "natural conversational pace, slightly imperfect, real",
        "visual_style": "Handheld selfie/phone-shot look, real home or everyday setting, natural lighting, direct-to-camera, no studio polish",
        "hook_type": "relatable first-person hook ('ok I have to tell you about this'), pattern interrupt",
        "cta_style": "casual, organic ('honestly just try it', 'link's in my bio'), non-salesy",
        "best_for": "almost any product — highest trust/conversion format on TikTok, beauty, gadgets, food, apps",
        "script_instruction": "Write in natural first-person as a real everyday person, NOT an ad. Open with a casual native hook like a friend texting you. Mention the product organically as part of your real life. Give an honest, specific opinion with a relatable detail. Avoid marketing buzzwords and perfect grammar — sound human, use filler-free but conversational language. End with a soft, non-pushy recommendation.",
        "visual_instruction": "Shoot to look like genuine phone footage: handheld selfie angle or talking directly to camera, everyday real-life setting (bedroom, kitchen, car, bathroom), natural/available lighting, no studio backdrop. Subject holds and uses the product casually and authentically. Keep it raw and relatable, not polished or commercial.",
    },

    "product_demo": {
        "name": "Product Demo",
        "description": "Shows product in action, features and benefits",
        "script_structure": "Open with product | Show features | Demonstrate benefits | Call to action",
        "tone": "informative, demonstrative, step-by-step",
        "pacing": "moderate to slow, allows time for each feature",
        "visual_style": "Product-focused, clear close-ups, multiple angles showing the product",
        "hook_type": "curiosity or benefit teaser",
        "cta_style": "direct, 'link in bio' or 'available now'",
        "best_for": "technical products, tools, features-focused items",
        "script_instruction": "Start with hook showing what problem it solves. Show 2-3 key features with demonstrations. End with clear CTA. Use instructional tone, speak directly about product features.",
        "visual_instruction": "Include clear product shots from multiple angles. Show the product being used in realistic scenarios. Highlight key features visually. Use product-focused b-roll.",
    },

    "testimonial": {
        "name": "Testimonial / Review",
        "description": "Personal experience and recommendation from user",
        "script_structure": "Personal introduction | Problem before | Experience with product | Results and benefits | Recommendation",
        "tone": "personal, authentic, conversational, emotional",
        "pacing": "natural, storytelling pace",
        "visual_style": "Character-focused, close-ups of face, personal setting, relatable environment",
        "hook_type": "emotional hook or relatable problem",
        "cta_style": "soft recommendation, 'you should try this', personal endorsement",
        "best_for": "skincare, wellness, lifestyle, any product needing social proof",
        "script_instruction": "Use first-person perspective throughout. Start with a relatable problem or situation. Share your authentic experience with the product. Include specific results or benefits you experienced. End with genuine recommendation. Sound natural and conversational, like talking to a friend.",
        "visual_instruction": "Focus on character's face and expressions. Show genuine reactions. Include before/during/after scenarios if applicable. Use personal, comfortable settings. Capture authentic moments and emotions.",
    },

    "tiktok_creative": {
        "name": "TikTok Creative",
        "description": "Trendy, fast-paced, music-driven viral content",
        "script_structure": "Trending hook | Entertainment first | Product integration | Trending audio sync",
        "tone": "fun, energetic, entertainment-focused, casual",
        "pacing": "fast, quick cuts, follows trending audio beats",
        "visual_style": "Dynamic cuts, trendy effects, trending backgrounds, fast transitions, product secondary",
        "hook_type": "trending audio, challenge format, entertainment value",
        "cta_style": "subtle product mention, implicit rather than explicit",
        "best_for": "young audience, viral potential, fun/lifestyle products",
        "script_instruction": "Lead with entertainment value, not product. Use trending phrases and audio hooks. Product should feel like a natural part of the trend, not forced. Keep it short and punchy. Match the pace of trending audios.",
        "visual_instruction": "Use trendy transitions and effects. Fast-paced cuts synced to audio. Incorporate trending formats (text overlays, quick cuts, trending backgrounds). Product appears naturally within the trend. Use trending colors and styles.",
    },

    "before_after": {
        "name": "Before / After",
        "description": "Shows transformation or problem-solution with visual impact",
        "script_structure": "Problem state | Application | Transformation | Results reveal | Call to action",
        "tone": "dramatic, impactful, satisfying, confident",
        "pacing": "quick reveal, slow build to transformation, fast show of results",
        "visual_style": "Split screen or transition-heavy, clear contrast between before and after, close-ups of transformation",
        "hook_type": "problem statement, surprise, visible transformation",
        "cta_style": "direct, 'get yours now', 'available at...'",
        "best_for": "beauty, fitness, skincare, transformative products",
        "script_instruction": "Clearly state the problem or starting point. Narrate the application process briefly. Build anticipation for the reveal. Dramatically show the after state. Emphasize the transformation with specific results.",
        "visual_instruction": "Show clear before state. Include application/process shots. Use dramatic transition to reveal after state. Include close-ups of transformation. Use visual effects to emphasize the change (slow-mo, cuts, reveals).",
    },

    "educational": {
        "name": "Educational / How-To",
        "description": "Teaching moment with value-add content and product integration",
        "script_structure": "Hook with knowledge | Step 1 | Step 2 | Step 3+ | Bonus tip with product | Call to action",
        "tone": "knowledgeable, helpful, friendly, authoritative",
        "pacing": "moderate, allows time for explanation of each step",
        "visual_style": "Clear step-by-step demonstrations, close-ups of technique, supporting visuals",
        "hook_type": "useful tip, knowledge hook, 'did you know'",
        "cta_style": "learn more, try this tip, link in bio for tools/resources",
        "best_for": "tutorials, wellness tips, cooking, productivity, DIY, any educational angle",
        "script_instruction": "Start with a clear, valuable tip or knowledge piece. Break down process into 3-5 clear steps. Use numbered or sequential language. Include your product as part of the solution. Share useful information whether or not someone buys your product.",
        "visual_instruction": "Show each step clearly with supporting visuals. Include close-ups of techniques. Use text overlays for step numbers. Show the full process. Incorporate product naturally into the steps.",
    },

    "trending_challenge": {
        "name": "Trending Challenge",
        "description": "Participates in or creates a trending challenge format",
        "script_structure": "Challenge introduction | Challenge execution with product | Challenge continuation | Tag/invite others",
        "tone": "playful, energetic, engaging, participatory",
        "pacing": "matches challenge format, often fast and rhythmic",
        "visual_style": "Matches challenge aesthetic, energetic, fun effects, other participants, group dynamics",
        "hook_type": "challenge format, trending sound, participation appeal",
        "cta_style": "tag friends, participate in challenge, 'your turn'",
        "best_for": "fun products, young audience, viral potential, social engagement",
        "script_instruction": "Introduce the challenge clearly. Participate authentically and enthusiastically. Integrate product naturally if it enhances the challenge. Use challenge-appropriate language and calls to action. Invite others to participate.",
        "visual_instruction": "Follow challenge visual conventions. Use challenge hashtags and formats. Include multiple participants if possible. Sync with challenge audio/trend. Make it look fun and participatory.",
    },

    "problem_solution": {
        "name": "Problem-Solution",
        "description": "Identifies relatable problem and shows product as solution",
        "script_structure": "Relatable problem | Problem agitation | Solution introduction | Benefits | Call to action",
        "tone": "empathetic, confident, persuasive, relatable",
        "pacing": "moderate, gives time to identify with problem",
        "visual_style": "Shows problem scenario, then solution in action, before-after style comparison",
        "hook_type": "relatable problem, pain point identification",
        "cta_style": "direct, 'solve this problem', 'available now'",
        "best_for": "any product, highly persuasive format, problem-focused niches",
        "script_instruction": "Start by identifying a common, relatable problem. Agitate the problem - show why it's frustrating. Present your product as the solution. Show specific benefits of the solution. End with clear call to action.",
        "visual_instruction": "Show the problem clearly in a relatable scenario. Show frustration or struggle. Show the product solving the problem. Demonstrate the positive outcome. Visual contrast between problem and solution states.",
    },
}

def get_video_type_instructions(video_type: str) -> dict:
    """Get instructions for a specific video type."""
    return VIDEO_TYPES.get(video_type, VIDEO_TYPES["product_demo"])

def get_video_type_script_instruction(video_type: str) -> str:
    """Get script writing instruction for a video type."""
    return get_video_type_instructions(video_type).get("script_instruction", "")

def get_video_type_visual_instruction(video_type: str) -> str:
    """Get visual generation instruction for a video type."""
    return get_video_type_instructions(video_type).get("visual_instruction", "")
