using BepInEx;

namespace Kibu5ZhCN
{
    // Compile/package probe only. Never patches methods or game assets.
    [BepInPlugin("local.kibu5.bootstrap", "Kibu5 Build Probe (No Translation)", "0.1.0")]
    [BepInProcess("kibu5.exe")]
    public sealed class BootstrapPlugin : BaseUnityPlugin
    {
        private void Awake()
        {
            Logger.LogInfo("Kibu5 bootstrap only; translation hooks are not implemented.");
        }
    }
}
