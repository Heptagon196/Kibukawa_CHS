using BepInEx;

namespace Kibu4ZhCN
{
    // Compile/package probe only. Never patches methods or game assets.
    [BepInPlugin("local.kibu4.bootstrap", "Kibu4 Build Probe (No Translation)", "0.1.0")]
    [BepInProcess("kibu4.exe")]
    public sealed class BootstrapPlugin : BaseUnityPlugin
    {
        private void Awake()
        {
            Logger.LogInfo("Kibu4 bootstrap only; translation hooks are not implemented.");
        }
    }
}
