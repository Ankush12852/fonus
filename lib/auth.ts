import { supabase } from './supabaseClient';

export const getSupabaseClient = () => supabase;

export const getCurrentUser = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    return session?.user || null;
};

export const onAuthChange = (callback: (user: any) => void) => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        callback(session?.user || null);
    });
    return subscription;
};

export const logout = async () => {
    await supabase.auth.signOut();
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_email');
    window.location.href = '/';
};
