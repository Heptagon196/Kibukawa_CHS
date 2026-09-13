using BepInEx;

namespace Kibu8ZhCN
{
    // Compile/package probe only. Never patches methods or game assets.
    [BepInPlugin("local.kibu8.bootstrap", "Kibu8 Build Probe (No Translation)", "0.1.0")]
    [BepInProcess("kibu8.exe")]
    public sealed class BootstrapPlugin : BaseUnityPlugin
    {
        private void Awake()
        {
            Logger.LogInfo("Kibu8 bootstrap only; translation hooks are not implemented.");
        }
    }
}
