using System;
using System.Reflection;
using BepInEx;
using HarmonyLib;
namespace KibukawaHistory
{
    [BepInPlugin("local.kibukawa.history", "Kibukawa Dialogue History", "1.6.5")]
    [BepInDependency("local.kibu10.zhcn", BepInDependency.DependencyFlags.HardDependency)]
    public sealed class HistoryPlugin : Gmode20050817DirectHistoryRuntime
    {
        private void Awake() { InitializeHistory(); }
        private void Update() { TickHistory(); }
        private void OnGUI() { DrawHistory(); }
        private void OnDestroy() { DisposeHistory(); }
        protected override string TranslateSpeaker(string speaker)
        {
            Type ui=AccessTools.TypeByName("Kibu10ZhCN.UiLocalization");
            MethodInfo translate=ui==null?null:AccessTools.Method(ui,"TranslateDisplay");
            return translate==null?speaker:(string)translate.Invoke(null,new object[]{speaker});
        }
    }
}
