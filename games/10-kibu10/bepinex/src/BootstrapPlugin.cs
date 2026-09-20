using BepInEx;

namespace Kibu10ZhCN
{
    // Compile/package probe only. Never patches methods or game assets.
    [BepInPlugin("local.kibu10.bootstrap", "Kibu10 Build Probe (No Translation)", "0.1.0")]
    [BepInProcess("kibu10.exe")]
    public sealed class BootstrapPlugin : BaseUnityPlugin
    {
        private void Awake()
        {
            Logger.LogInfo("Kibu10 bootstrap only; translation hooks are not implemented.");
        }
    }
}
