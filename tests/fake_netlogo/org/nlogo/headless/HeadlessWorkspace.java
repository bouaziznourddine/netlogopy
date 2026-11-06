package org.nlogo.headless;

/** Minimal stand-in for NetLogo's HeadlessWorkspace, used by netlogopy's tests. */
public class HeadlessWorkspace {
    public String model;
    public boolean disposed;
    private double ticks;
    private int nextWho;

    public static HeadlessWorkspace newInstance() { return new HeadlessWorkspace(); }

    public void open(String path, boolean autoInstallLibs) {
        if (!new java.io.File(path).isFile()) {
            throw new IllegalStateException("cannot open " + path);
        }
        model = path;
    }

    public void command(String source) { Fake.command(source); if (source.equals("tick")) ticks++; }

    public Object report(String source) {
        if (source.equals("ticks")) return Double.valueOf(ticks);
        if (source.startsWith("create-pyturtle-xyid")) return Double.valueOf(nextWho++);
        return Fake.report(source);
    }

    public void exportView(String file, String format) { }

    public void dispose() { disposed = true; }
}
