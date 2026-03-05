# LVGL MVU Example PR Learnings

## Key Insights
- `lv_label_set_text_static()` requires string to remain alive
- Caching strings on the `App` ensures string lifetime
- Memory soak test is critical for LVGL retained-mode UI

## Workflow Notes
- Verified locally with full device test cycle
- Minimal PR with focused changes
- Updated changelog with concise description

## Technical Constraints
- ESP32 requires specific partition table for LVGL
- String lifetime management is crucial in retained mode
- Device testing is mandatory for embedded UI code

## Future Improvements
- Add more comprehensive memory tracking
- Create generic string lifetime management utility
- Expand LVGL example to cover more widget interactions