using BepInEx;

namespace Kibu7ZhCN
{
    // Compile/package probe only. Never patches methods or game assets.
    [BepInPlugin("local.kibu7.bootstrap", "Kibu7 Build Probe (No Translation)", "0.1.0")]
    [BepInProcess("kibu7.exe")]
    public sealed class BootstrapPlugin : BaseUnityPlugin
    {
        private void Awake()
        {
            Logger.LogInfo("Kibu7 bootstrap only; translation hooks are not implemented.");
        }
    }
}
