using System;
using Kibukawa.Engine.UnityUI;

namespace Kibu9ZhCN
{
    // Game-specific policy; the shared runtime owns Unity Text/localization hooks.
    public sealed class UiLocalization : UiLocalizationRuntime
    {
        private const string ConfirmationSource = "「{0}」で宜しいですか？";
        private const string ConfirmationSuffix = "」で宜しいですか？";

        public new static void Initialize(Action<string> logger = null)
        {
            Owner = "heptagon.kibu9.zhcn.ui";
            Exact = UiLocalizationData.Exact;
            Keys = UiLocalizationData.Keys;
            IsExcluded = IsTechnicalString;
            TranslateSpecial = TranslateConfirmation;
            FontNames = new[] { "Microsoft YaHei", "SimSun", "Noto Sans CJK SC", "Source Han Sans SC" };
            UiLocalizationRuntime.Initialize(logger);
        }

        private static bool IsTechnicalString(string value)
        {
            return value == "停止" || value == "消去" || value == "全"
                || value == "変えないでお願いします" || value == "ＦＯ" || value == "漢字";
        }

        private static string TranslateConfirmation(string source)
        {
            string result;
            if (source.StartsWith("「", StringComparison.Ordinal)
                && source.EndsWith(ConfirmationSuffix, StringComparison.Ordinal)
                && source.Length >= ConfirmationSuffix.Length + 1
                && UiLocalizationData.Exact.TryGetValue(ConfirmationSource, out result))
            {
                string name = source.Substring(1, source.Length - 1 - ConfirmationSuffix.Length);
                return result.Replace("{0}", name);
            }
            return source;
        }
    }
}
