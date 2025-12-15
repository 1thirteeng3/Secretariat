import { View, Text, TouchableOpacity, Alert, FlatList } from 'react-native';
import { useState, useEffect } from 'react';
import { Mic, Plus, Trash2 } from 'lucide-react-native';
import { Audio } from 'expo-av';
// Note: lucide-react-native needs to be installed, for now using Text placeholders if icons missing

export default function InboxScreen() {
    const [recording, setRecording] = useState<Audio.Recording | null>(null);
    const [permissionResponse, requestPermission] = Audio.usePermissions();
    const [recordings, setRecordings] = useState<any[]>([]);
    const [isRecording, setIsRecording] = useState(false);

    async function startRecording() {
        try {
            if (permissionResponse?.status !== 'granted') {
                console.log('Requesting permission..');
                await requestPermission();
            }

            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
            });

            console.log('Starting recording..');
            const { recording } = await Audio.Recording.createAsync(
                Audio.RecordingOptionsPresets.HIGH_QUALITY
            );
            setRecording(recording);
            setIsRecording(true);
            console.log('Recording started');
        } catch (err) {
            console.error('Failed to start recording', err);
            Alert.alert('Failed to start recording', JSON.stringify(err));
        }
    }

    async function stopRecording() {
        console.log('Stopping recording..');
        if (!recording) return;

        setIsRecording(false);
        setRecording(null);
        await recording.stopAndUnloadAsync();
        const uri = recording.getURI();
        console.log('Recording stopped and stored at', uri);

        // Mock saving to DB
        const newRef = {
            id: Date.now().toString(),
            uri: uri,
            timestamp: new Date().toLocaleTimeString(),
            duration: "0:05" // Mock duration
        };
        setRecordings(prev => [newRef, ...prev]);
    }

    return (
        <View className="flex-1 px-6 pt-12 bg-slate-950">
            <Text className="text-white text-3xl font-bold mb-8 font-mono">Inbox</Text>

            {/* Voice Recorder Button - The "Big Red Button" */}
            <View className="flex-1 items-center justify-center">
                <TouchableOpacity
                    className={`w-40 h-40 rounded-full items-center justify-center shadow-lg border-4 transition-all ${isRecording
                            ? "bg-red-500 border-red-400 shadow-red-500/50 scale-110"
                            : "bg-red-700 border-slate-800 shadow-red-900"
                        }`}
                    activeOpacity={0.8}
                    onPressIn={startRecording}
                    onPressOut={stopRecording}
                >
                    <Mic size={48} color="white" />
                </TouchableOpacity>
                <Text className={`mt-8 font-mono tracking-widest text-sm uppercase ${isRecording ? "text-red-400 animate-pulse" : "text-slate-500"}`}>
                    {isRecording ? "Recording..." : "Hold to Record"}
                </Text>
            </View>

            {/* Recent Captures List */}
            <View className="flex-1 mt-8">
                <Text className="text-slate-500 font-mono text-xs uppercase mb-4">Pending Sync</Text>
                <FlatList
                    data={recordings}
                    keyExtractor={item => item.id}
                    renderItem={({ item }) => (
                        <View className="bg-slate-900 p-4 rounded-lg mb-3 flex-row items-center justify-between border border-slate-800">
                            <View className="flex-row items-center space-x-3">
                                <View className="w-8 h-8 rounded-full bg-slate-800 items-center justify-center">
                                    <Mic size={16} color="#94a3b8" />
                                </View>
                                <View>
                                    <Text className="text-slate-200 font-bold text-sm">Voice Note</Text>
                                    <Text className="text-slate-500 text-xs">{item.timestamp}</Text>
                                </View>
                            </View>
                            <Text className="text-orange-500 font-mono text-xs">Waiting</Text>
                        </View>
                    )}
                />
            </View>

            {/* Floating Action Button for Text */}
            <TouchableOpacity className="absolute bottom-10 right-8 w-14 h-14 bg-orange-600 rounded-full items-center justify-center shadow-lg shadow-orange-900/40">
                <Plus size={28} color="white" />
            </TouchableOpacity>
        </View>
    );
}
