package org.nlogo.app;

import org.nlogo.headless.Fake;

/** Minimal stand-in for NetLogo's App, used by netlogopy's tests. */
public class App {
    private static volatile App instance;
    public static int mainCalls;
    public String model;
    public boolean openedOnEventThread;
    private int nextWho;

    public static void main(String[] args) {
        mainCalls++;
        new Thread(() -> {
            try { Thread.sleep(300); } catch (InterruptedException e) { }
            instance = new App();
        }).start();
    }

    public static App app() { return instance; }

    public void open(String path, boolean autoInstallLibs) {
        openedOnEventThread = java.awt.EventQueue.isDispatchThread();
        model = path;
    }

    public void command(String source) { Fake.command(source); }

    public Object report(String source) {
        if (source.startsWith("create-pyturtle-xyid")) return Double.valueOf(nextWho++);
        return Fake.report(source);
    }
}
