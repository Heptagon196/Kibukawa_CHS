using BepInEx;

namespace Kibu6ZhCN
{
    // Compile/package probe only. Never patches methods or game assets.
    [BepInPlugin("local.kibu6.bootstrap", "Kibu6 Build Probe (No Translation)", "0.1.0")]
    [BepInProcess("kibu6.exe")]
    public sealed class BootstrapPlugin : BaseUnityPlugin
    {
        private void Awake()
        {
            Logger.LogInfo("Kibu6 bootstrap only; translation hooks are not implemented.");
        }
    }
}
