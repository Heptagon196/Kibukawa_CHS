using BepInEx;

namespace Kibu2ZhCN
{
    // Compile/package probe only. Never patches methods or game assets.
    [BepInPlugin("local.kibu2.bootstrap", "Kibu2 Build Probe (No Translation)", "0.1.0")]
    [BepInProcess("kibu2.exe")]
    public sealed class BootstrapPlugin : BaseUnityPlugin
    {
        private void Awake()
        {
            Logger.LogInfo("Kibu2 bootstrap only; translation hooks are not implemented.");
        }
    }
}
