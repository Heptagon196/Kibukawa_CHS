using BepInEx;
using KibukawaHistory;

namespace Kibu9ZhCN
{
    [BepInPlugin("local.kibukawa.history", "Kibukawa Dialogue History", "1.0.0")]
    [BepInDependency("local.kibu9.zhcn", BepInDependency.DependencyFlags.HardDependency)]
    public sealed class HistoryPlugin : Gmode20050117HistoryRuntime
    {
        private void Awake() { InitializeHistory(); }
        private void Update() { TickHistory(); }
        private void OnGUI() { DrawHistory(); }
        private void OnDestroy() { DisposeHistory(); }

        /// <summary>
        /// Nameplates are already Chinese: the text plugin replaces NAMAE_SETTEI's
        /// first StringRead before the game stores it, and the history reads the stored
        /// array. Nothing further to translate here.
        /// </summary>
        protected override string TranslateSpeaker(string speaker) { return speaker; }
    }
}
