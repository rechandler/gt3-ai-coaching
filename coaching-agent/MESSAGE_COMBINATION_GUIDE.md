# Message Combination System

## Overview

The GT3 AI Coaching system now includes an intelligent message combination feature that automatically combines similar coaching messages into concise, actionable summaries. This addresses the issue where multiple similar messages (like the three throttle-related messages you experienced) would be displayed separately, creating information overload.

## Problem Solved

**Before**: Multiple similar messages would appear separately:
```
[throttle] Focus on getting the car rotated before getting back on the throttle.
[throttle] Wait longer before applying throttle in corners for better balance.
[throttle] Patience with throttle application will improve your corner exit speed.
```

**After**: Similar messages are combined into one concise message:
```
[throttle] Focus on throttle patience: Wait longer before applying throttle in corners for better balance and exit speed.
```

## How It Works

### Message Combination Logic

1. **Time Window**: Messages within 3 seconds of each other are candidates for combination
2. **Category Matching**: Only messages of the same category (e.g., 'throttle', 'braking') are combined
3. **Keyword Analysis**: Messages with similar keywords are identified for combination
4. **Template Application**: Combined messages use predefined templates for clarity

### Combination Patterns

The system recognizes these coaching categories and combines them intelligently:

- **Throttle**: Combines messages about throttle timing, patience, and corner exit technique
- **Braking**: Combines messages about brake timing, pressure, and entry technique  
- **Cornering**: Combines messages about corner entry, apex, and exit technique
- **Consistency**: Combines messages about smooth inputs and technique consistency

### Configuration

The message combination system is configurable via `config.py`:

```python
'message_combination': {
    'enabled': True,
    'combination_window': 3.0,  # seconds to look for similar messages
    'min_keyword_matches': 2,   # minimum keyword matches to consider combination
    'combine_categories': ['throttle', 'braking', 'cornering', 'consistency'],
    'max_combined_messages': 5   # maximum number of messages to combine
}
```

## Implementation Details

### MessageCombiner Class

The `MessageCombiner` class handles the intelligent combination of messages:

- **Keyword Matching**: Uses predefined keywords for each category to identify similar messages
- **Template System**: Applies category-specific templates for combined messages
- **Priority Handling**: Uses the highest priority from the combined messages
- **Confidence Averaging**: Calculates average confidence from combined messages

### Integration with Message Queue

The combination logic is integrated into the `CoachingMessageQueue`:

- **Automatic Detection**: Checks for combination opportunities when adding new messages
- **Queue Management**: Replaces original messages with combined versions
- **Statistics Tracking**: Tracks how many messages have been combined

## Benefits

1. **Reduced Information Overload**: Fewer, more focused messages
2. **Better User Experience**: Clearer, actionable coaching advice
3. **Maintained Context**: All important information is preserved in concise form
4. **Configurable**: Can be enabled/disabled and tuned per user preferences

## Testing

The system includes comprehensive testing via `test_message_combination.py`:

```bash
cd coaching-agent
python test_message_combination.py
```

This test verifies that:
- Similar messages are correctly identified
- Messages are properly combined using templates
- Queue statistics are accurately tracked
- Combined messages maintain proper priority and confidence

## Usage

The message combination system works automatically - no changes needed to existing code. When similar coaching messages are generated within the time window, they will be automatically combined into a single, more concise message.

## Future Enhancements

- **Dynamic Templates**: AI-generated templates based on message content
- **User Preferences**: Allow users to customize combination behavior
- **Category Expansion**: Add more coaching categories for combination
- **Smart Timing**: Adjust combination window based on driving context 