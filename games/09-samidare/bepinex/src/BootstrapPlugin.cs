using BepInEx;

namespace Kibu9ZhCN
{
    // Compile/package probe only. Never patches methods or game assets.
    [BepInPlugin("local.kibu9.bootstrap", "Kibu9 Build Probe (No Translation)", "0.1.0")]
    [BepInProcess("kibu9.exe")]
    public sealed class BootstrapPlugin : BaseUnityPlugin
    {
        private void Awake()
        {
            Logger.LogInfo("Kibu9 bootstrap only; translation hooks are not implemented.");
        }
    }
}
