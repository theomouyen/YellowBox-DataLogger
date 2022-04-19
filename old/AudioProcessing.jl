### A Pluto.jl notebook ###
# v0.14.5

using Markdown
using InteractiveUtils

# This Pluto notebook uses @bind for interactivity. When running this notebook outside of Pluto, the following 'mock version' of @bind gives bound variables a default value (instead of an error).
macro bind(def, element)
    quote
        local el = $(esc(element))
        global $(esc(def)) = Core.applicable(Base.get, el) ? Base.get(el) : missing
        el
    end
end

# ╔═╡ 5900843c-b18d-11eb-329e-6b13a4c8b6cb
using WAV,CSV,DataFrames,Statistics,SampledSignals,DelimitedFiles,
	PlutoUI,Plots,DSP,FFTW

# ╔═╡ bf336b57-c024-4905-94fa-b0e0932b72db
md"# Audio Processing"

# ╔═╡ 9dc33605-6435-4397-a8f4-ae8354382b02
PlutoUI.TableOfContents()

# ╔═╡ 63b90b21-538a-41a7-b40e-b3e129cad03e
md"""## Audio sample """

# ╔═╡ 2bb59aa8-7903-4568-90c9-5e76d9e58528
md"## Helper Functions"

# ╔═╡ 97b4557f-2abd-40b6-96e7-dde90197d492
function read_audio_csv(fname)
	d= readdlm(fname,';',skipstart=3)
	f=Int(round(mean(1.0 ./ diff(d[:,1]))))
	dmax=maximum(d[:,2:end])
	d[:,2:end]/dmax,f
end

# ╔═╡ a849634d-9276-4f03-95f4-6e2da215da41
function plot_spectrogramm(signal)
	fs=signal.samplerate
    S = spectrogram(signal.data[:,1], convert(Int, 25e-3*fs),
                    convert(Int, 10e-3*fs); fs=fs,window=hanning)
	t = time(S)
    f = freq(S)
    heatmap(t,f,log10.(power(S)))
end


# ╔═╡ 268103da-39ae-4aee-a7b6-78c1cf79dd7e
function read_experiment_dir(data)
	d=readdir(data);
	ext=r"^.*\.(csv|wav)$";
	files=d[occursin.(ext,d)];
end

# ╔═╡ 01988c65-93af-4c42-88be-5cd5988e209f
begin
	data="/home/jls/data/2021-Monochord/raw/"
	files=read_experiment_dir(data)
end

# ╔═╡ 6bbb1bc2-3595-45ff-9f10-4a5c992c82e2
md"""
Choose file
$(@bind experiment Select(files))
"""

# ╔═╡ b338cb9c-5b28-4003-aa4a-4b76d85216f9
begin
	global sig,fs
	fname=joinpath(data,experiment)
	samples,fs=read_audio_csv(fname)
	sig=SampleBuf(samples,fs)
end

# ╔═╡ 31a38a99-aea6-45db-903d-625bd31c54fd
fs

# ╔═╡ 6f8d7090-d8bc-4646-844c-dfe2aff7005b
begin
	p1=plot(domain(sig),sig);
	SIG=fft(sig)/nframes(sig);
	p2=plot(domain(SIG[100Hz..1000Hz]).+100,2*abs.(SIG[100Hz..1000Hz]));
	p3=plot_spectrogramm(sig)
	plot(p1,p2,p3,layout=(3,1))
end

# ╔═╡ Cell order:
# ╟─bf336b57-c024-4905-94fa-b0e0932b72db
# ╟─9dc33605-6435-4397-a8f4-ae8354382b02
# ╟─5900843c-b18d-11eb-329e-6b13a4c8b6cb
# ╠═01988c65-93af-4c42-88be-5cd5988e209f
# ╟─6bbb1bc2-3595-45ff-9f10-4a5c992c82e2
# ╠═b338cb9c-5b28-4003-aa4a-4b76d85216f9
# ╠═31a38a99-aea6-45db-903d-625bd31c54fd
# ╟─63b90b21-538a-41a7-b40e-b3e129cad03e
# ╟─6f8d7090-d8bc-4646-844c-dfe2aff7005b
# ╟─2bb59aa8-7903-4568-90c9-5e76d9e58528
# ╟─97b4557f-2abd-40b6-96e7-dde90197d492
# ╟─a849634d-9276-4f03-95f4-6e2da215da41
# ╟─268103da-39ae-4aee-a7b6-78c1cf79dd7e
