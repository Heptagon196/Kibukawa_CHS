using UnityEngine;
namespace KibukawaHistory
{
    // Keep the native audio clock/callbacks intact while an overlay owns input.
    // The adapter supplies the effect channel; never change the global listener.
    public sealed class HistoryAudioMute
    {
        private AudioSource source;
        private bool previous;
        public void Suspend(AudioSource value)
        {
            if(ReferenceEquals(source,value)) return;
            Restore();
            if(value==null) return;
            source=value;previous=value.mute;value.mute=true;
        }
        public void Restore()
        {
            if(source!=null) source.mute=previous;
            source=null;
        }
    }
}
