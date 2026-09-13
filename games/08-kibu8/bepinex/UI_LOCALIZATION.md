# UI runtime integration

Compile `src/UiLocalization.cs` and generated `src/UiLocalizationData.cs` alongside the main plugin using the shared BepInEx build layer. Both use `Kibu8ZhCN`; required existing references are Harmony, UnityEngine and UnityEngine.UI.

Call `UiLocalization.Initialize(message => Logger.LogInfo(message))` from the plugin's Unity main-thread initialization, `UiLocalization.Update()` from `Update`, and `UiLocalization.Dispose()` from `OnDestroy`. Initialization is idempotent. Register script name and bookmark translations with `RegisterDisplayTranslation(source, target)`; registering before initialization is supported. Conflicting exact translations throw instead of silently changing a label. `GetChineseFont()` returns the shared dynamic system font, or null when unavailable, for the note GUI.

Regenerate data with `python games/08-kibu8/scripts/generate_ui_data.py` from the repository root after changing any of the three `work/ui-*.zh-CN.json` catalogs. The generated file records their SHA-256 hashes. Only explicit player/legacy UI and already reviewed duplicate classifications enter the catalog. Excluded templates/debug rows and technical sentinels are omitted. CRLF and LF sources have corresponding exact variants.

## Display boundaries and evidence

The inspected `research/kibu8-assembly.json` establishes these hooks:

- `Steezy.Localize.Localization.Get(string)`: postfix replaces reviewed localization keys.
- `UnityEngine.UI.Text.text` and `Text.OnEnable`: translate exact visible labels, including repeated assignments and newly enabled objects. A two-second sweep covers already loaded serialized labels and inactive objects. Actual `InputField.textComponent` values remain untouched; placeholders can translate.
- `Socotra.UI.StGraphics.DrawString(string,int,int)`: translates the final drawing argument before it is converted to a character array and reaches the main plugin's `DrawCharImpl` glyph renderer.
- `DrawChars(char[],int,int,int,int)`: translates a copy of the offset/length slice (parameter indices 3 and 4), never overwriting the caller's script/name/bookmark buffer.
- `CharacterInputDialog` formats `「{0}」で宜しいですか？` before assigning the label. A guarded prefix/suffix match handles this one formatted sentence and preserves the entire inserted player name.

`CanvasEx.SoftKeyMenu` compares and stores original `戻る`/sentinel labels; `CharacterInputKeyItem.Init` stores the original keyboard string separately from visible Text. Neither method's fields, arguments nor IL literals are rewritten. The exact technical strings `停止`, `消去`, `全`, `変えないでお願いします`, `ＦＯ`, `漢字` cannot be registered. Persistence remains Japanese/SJIS-compatible while final drawing can use Chinese.

UI fonts use Microsoft YaHei with Chinese system fallbacks, retained across scene changes. Original Text font/layout properties are retained and restored on disposal; input values keep their layout. Disposal unpatches only the module's Harmony owner and destroys only its own font.

Static catalog generation completed with 62 exact strings and 15 localization keys. No game build, install or window operation was performed for this module. Real layout, legacy renderer sizing and glyph appearance still require the user's in-game verification.
