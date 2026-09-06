using BepInEx;

namespace Kibu3ZhCN
{
    // Compile/package probe only. Never patches methods or game assets.
    [BepInPlugin("local.kibu3.bootstrap", "Kibu3 Build Probe (No Translation)", "0.1.0")]
    [BepInProcess("kibu3.exe")]
    public sealed class BootstrapPlugin : BaseUnityPlugin
    {
        private void Awake()
        {
            Logger.LogInfo("Kibu3 bootstrap only; translation hooks are not implemented.");
        }
    }
}
