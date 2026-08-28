// RaC implementation adapted into this independent repository.
// It implements the manuscript's cluster functions, rake/compress bottom-up
// hierarchy and top-down threshold recovery using exact integer arithmetic.

#include "parametric_closure/algorithms.hpp"
#include "parametric_closure/instance.hpp"

#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <limits>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace pcf {
namespace {
using i64 = std::int64_t;
using i128 = __int128_t;

struct IntArc { int tail=-1, head=-1; };
struct IntInstance {
    int n=0;
    std::vector<i64> p,w;
    std::vector<IntArc> arcs;
};
struct IntMacroitem { std::vector<int> nodes; i64 p=0,w=0; };
struct IntSequence { std::vector<IntMacroitem> macroitems; };


struct Rat {
    i64 num=0, den=1; // den>0
};
static Rat make_rat(i64 n, i64 d) {
    if(d==0) throw std::runtime_error("zero denominator");
    if(d<0){n=-n;d=-d;}
    i64 g=std::gcd(n<0?-n:n,d);
    if(g){n/=g;d/=g;}
    return {n,d};
}
static int cmp_rat(const Rat&a,const Rat&b){
    i128 l=(i128)a.num*b.den, r=(i128)b.num*a.den;
    return (l>r)-(l<r);
}
static bool rat_eq(const Rat&a,const Rat&b){return cmp_rat(a,b)==0;}

using Counters = RaCStats;

struct Line { i64 P=0,W=0; };
struct Envelope {
    bool feasible=false;
    std::vector<Line> lines;
};

static Rat intersect_lines(const Line&a,const Line&b,Counters* = nullptr){
    // a.W > b.W, equality point a.P-lambda*a.W=b.P-lambda*b.W
    if(!(a.W>b.W)) throw std::runtime_error("invalid envelope line order");
    return make_rat(a.P-b.P,a.W-b.W);
}
static int cmp_intersections(const Line&a,const Line&b,const Line&c,const Line&d,Counters*ct=nullptr){
    // compare intersection(a,b) vs intersection(c,d) without constructing reductions
    if(ct){ct->rational_comparisons++;ct->line_comparisons++;}
    i128 l=(i128)(a.P-b.P)*(c.W-d.W);
    i128 r=(i128)(c.P-d.P)*(a.W-b.W);
    return (l>r)-(l<r);
}

static Envelope hull_from_lines(std::vector<Line> v, Counters&ct) {
    ct.hull_calls++;
    if(v.empty()) return {};
    std::sort(v.begin(),v.end(),[](const Line&a,const Line&b){
        if(a.W!=b.W) return a.W>b.W;
        return a.P>b.P;
    });
    std::vector<Line> ded;
    ded.reserve(v.size());
    for(const auto&l:v){
        ct.lines_scanned++;
        if(!ded.empty() && ded.back().W==l.W){
            if(l.P>ded.back().P) ded.back().P=l.P;
        } else ded.push_back(l);
    }
    std::vector<Line> h; h.reserve(ded.size());
    for(const auto&l:ded){
        while(h.size()>=2){
            // if intersection(h[-2],h[-1]) >= intersection(h[-1],l), middle inactive
            int c=cmp_intersections(h[h.size()-2],h[h.size()-1],h[h.size()-1],l,&ct);
            if(c>=0) h.pop_back(); else break;
        }
        h.push_back(l);
    }
    Envelope e; e.feasible=true; e.lines=std::move(h); return e;
}
static Envelope zero_env(){Envelope e;e.feasible=true;e.lines={{0,0}};return e;}

static Rat next_bp(const Envelope&e,size_t i,Counters*ct=nullptr){
    return intersect_lines(e.lines[i],e.lines[i+1],ct);
}

static Envelope env_sum(const Envelope&a,const Envelope&b,Counters&ct){
    ct.envelope_sum_calls++;
    if(!a.feasible||!b.feasible) return {};
    size_t i=0,j=0;
    std::vector<Line> out; out.reserve(a.lines.size()+b.lines.size());
    auto push=[&](){
        Line l{a.lines[i].P+b.lines[j].P,a.lines[i].W+b.lines[j].W};
        if(out.empty()||out.back().P!=l.P||out.back().W!=l.W) out.push_back(l);
    };
    push();
    while(i+1<a.lines.size()||j+1<b.lines.size()){
        if(i+1==a.lines.size()){++j;push();continue;}
        if(j+1==b.lines.size()){++i;push();continue;}
        Rat x=next_bp(a,i,&ct), y=next_bp(b,j,&ct);
        int c=cmp_rat(x,y); ct.rational_comparisons++;
        if(c<0) ++i; else if(c>0) ++j; else {++i;++j;}
        push();
    }
    return hull_from_lines(std::move(out),ct);
}
static Envelope env_shift(const Envelope&a,i64 P,i64 W,Counters&ct){
    if(!a.feasible) return {};
    Envelope r; r.feasible=true; r.lines.reserve(a.lines.size());
    for(auto l:a.lines){ct.lines_scanned++; r.lines.push_back({l.P+P,l.W+W});}
    return r;
}
static Envelope env_max(const Envelope&a,const Envelope&b,Counters&ct){
    ct.envelope_max_calls++;
    if(!a.feasible) return b;
    if(!b.feasible) return a;
    std::vector<Line> v; v.reserve(a.lines.size()+b.lines.size());
    size_t i=0,j=0;
    while(i<a.lines.size()||j<b.lines.size()){
        if(j==b.lines.size()||(i<a.lines.size() && a.lines[i].W>b.lines[j].W)) v.push_back(a.lines[i++]);
        else if(i==a.lines.size()||b.lines[j].W>a.lines[i].W) v.push_back(b.lines[j++]);
        else { v.push_back(a.lines[i].P>=b.lines[j].P?a.lines[i]:b.lines[j]); ++i;++j; }
    }
    return hull_from_lines(std::move(v),ct);
}

static std::vector<Rat> envelope_breakpoints(const Envelope&e,Counters&ct){
    std::vector<Rat> r;
    if(!e.feasible||e.lines.size()<2) return r;
    r.reserve(e.lines.size()-1);
    for(size_t i=0;i+1<e.lines.size();++i) r.push_back(next_bp(e,i,&ct));
    return r;
}
static std::vector<Rat> merge_events_linear(const std::vector<std::vector<Rat>>&lists,Counters&ct){
    std::vector<size_t> pos(lists.size(),0);
    std::vector<Rat> out;
    while(true){
        int best=-1;
        for(int k=0;k<(int)lists.size();++k){
            if(pos[k]>=lists[k].size()) continue;
            if(best<0 || cmp_rat(lists[k][pos[k]],lists[best][pos[best]])<0){best=k;ct.rational_comparisons++;}
        }
        if(best<0) break;
        Rat q=lists[best][pos[best]];
        if(out.empty()||!rat_eq(out.back(),q)) out.push_back(q);
        for(int k=0;k<(int)lists.size();++k){
            while(pos[k]<lists[k].size()&&rat_eq(lists[k][pos[k]],q)){++pos[k];ct.rational_comparisons++;}
        }
    }
    return out;
}

struct XEdge {
    int a=-1,b=-1;
    enum Kind { PREC, EQUAL } kind=PREC;
    int tail=-1,head=-1; // expanded endpoints for PREC
};
struct Expanded {
    int n=0;
    std::vector<i64> p,w;
    std::vector<XEdge> edges;
    std::vector<int> representative; // original id for objective copy, -1 otherwise
    std::vector<int> original_objective_copy;
    std::vector<int> isolated_originals;
};

static Expanded expand_degree_three(const IntInstance&ins){
    Expanded ex; ex.original_objective_copy.assign(ins.n,-1);
    std::vector<std::vector<std::pair<int,int>>> inc(ins.n); // (edge index, endpoint side 0 tail/1 head)
    for(int e=0;e<(int)ins.arcs.size();++e){
        inc[ins.arcs[e].tail].push_back({e,0});
        inc[ins.arcs[e].head].push_back({e,1});
    }
    std::vector<std::array<int,2>> port(ins.arcs.size(),std::array<int,2>{-1,-1});
    for(int v=0;v<ins.n;++v){
        int d=(int)inc[v].size();
        if(d==0){ex.isolated_originals.push_back(v);continue;}
        std::vector<int> copies(d);
        for(int k=0;k<d;++k){
            int id=ex.n++;
            copies[k]=id;
            ex.p.push_back(k==0?ins.p[v]:0);
            ex.w.push_back(k==0?ins.w[v]:0);
            ex.representative.push_back(k==0?v:-1);
            if(k==0) ex.original_objective_copy[v]=id;
            auto [eid,side]=inc[v][k]; port[eid][side]=id;
        }
        for(int k=0;k+1<d;++k){
            XEdge ee;ee.a=copies[k];ee.b=copies[k+1];ee.kind=XEdge::EQUAL;
            ex.edges.push_back(ee);
        }
    }
    for(int e=0;e<(int)ins.arcs.size();++e){
        int a=port[e][0], b=port[e][1];
        if(a<0||b<0) throw std::runtime_error("missing port");
        XEdge ee;ee.a=a;ee.b=b;ee.kind=XEdge::PREC;ee.tail=a;ee.head=b;
        ex.edges.push_back(ee);
    }
    return ex;
}

struct Cluster {
    enum Type { LEAF, JOIN, INTERNALIZE } type=LEAF;
    int child1=-1, child2=-1;
    int shared=-1; // JOIN shared vertex
    int internalized=-1; // vertex charged/removed at this node, else -1
    std::array<int,2> boundary{-1,-1};
    int bsz=0;
    std::array<Envelope,4> f;
    int depth=1;
    int leaf_edge=-1;
};

static int state_bit(const Cluster&c,int state,int vertex){
    for(int k=0;k<c.bsz;++k) if(c.boundary[k]==vertex) return (state>>k)&1;
    throw std::runtime_error("vertex not in boundary");
}
static int make_state_for_child(const Cluster&child,const Cluster&parent,int pstate,int special,int x){
    int s=0;
    for(int k=0;k<child.bsz;++k){
        int v=child.boundary[k]; int val;
        if(v==special) val=x;
        else val=state_bit(parent,pstate,v);
        s|=(val<<k);
    }
    return s;
}

class RaCSolver {
public:
    explicit RaCSolver(const IntInstance&i):ins(i),ex(expand_degree_three(i)){
        ct.expanded_vertices=ex.n;ct.expanded_edges=ex.edges.size();
        theta_exp.resize(ex.n); theta_known.assign(ex.n,false);
    }
    IntSequence solve(){
        std::vector<Rat> theta_orig(ins.n);
        for(int v:ex.isolated_originals) theta_orig[v]=make_rat(ins.p[v],ins.w[v]);
        if(ex.n>0){
            build_components_and_hierarchy();
            for(int root:roots) recover(root);
            for(int v=0;v<ins.n;++v){
                if(ex.original_objective_copy[v]>=0){
                    int x=ex.original_objective_copy[v];
                    if(!theta_known[x]) throw std::runtime_error("threshold missing");
                    theta_orig[v]=theta_exp[x];
                }
            }
        }
        // group exact equal thresholds descending
        std::vector<int> order(ins.n);std::iota(order.begin(),order.end(),0);
        std::sort(order.begin(),order.end(),[&](int a,int b){int c=cmp_rat(theta_orig[a],theta_orig[b]);return c?c>0:a<b;});
        IntSequence seq;
        for(int v:order){
            if(seq.macroitems.empty()) seq.macroitems.push_back({});
            else {
                int prev=seq.macroitems.back().nodes.front();
                if(!rat_eq(theta_orig[prev],theta_orig[v])) seq.macroitems.push_back({});
            }
            auto &m=seq.macroitems.back();m.nodes.push_back(v);m.p+=ins.p[v];m.w+=ins.w[v];
        }
        ct.clusters=clusters.size();
        ct.pieces_stored=0; ct.estimated_bytes=clusters.capacity()*sizeof(Cluster);
        for(const auto&c:clusters){for(int s=0;s<(1<<c.bsz);++s){ct.pieces_stored+=c.f[s].lines.size();ct.estimated_bytes+=c.f[s].lines.capacity()*sizeof(Line);}}
        return seq;
    }
    const Counters& counters()const{return ct;}
    const std::vector<Rat>& expanded_thresholds()const{return theta_exp;}
private:
    const IntInstance&ins; Expanded ex; Counters ct;
    std::vector<Cluster> clusters; std::vector<int> roots;
    std::vector<Rat> theta_exp; std::vector<char> theta_known;

    int add_leaf(int eid){
        const auto&e=ex.edges[eid]; Cluster c;c.type=Cluster::LEAF;c.leaf_edge=eid;c.bsz=2;
        if(e.a<e.b)c.boundary={e.a,e.b};else c.boundary={e.b,e.a};
        for(int st=0;st<4;++st){
            int xa=state_bit(c,st,e.a),xb=state_bit(c,st,e.b);bool ok;
            if(e.kind==XEdge::EQUAL) ok=xa==xb;
            else {int xt=state_bit(c,st,e.tail),xh=state_bit(c,st,e.head);ok=xt<=xh;}
            if(ok)c.f[st]=zero_env();
        }
        clusters.push_back(std::move(c)); ct.max_cluster_depth=std::max<std::uint64_t>(ct.max_cluster_depth,1);return clusters.size()-1;
    }
    static std::vector<int> sorted_boundary(std::initializer_list<int> z){
        std::vector<int> v;for(int x:z)if(x>=0)v.push_back(x);std::sort(v.begin(),v.end());v.erase(std::unique(v.begin(),v.end()),v.end());return v;
    }
    int add_join(int A,int B,int shared,const std::vector<int>&pb){
        Cluster c;c.type=Cluster::JOIN;c.child1=A;c.child2=B;c.shared=shared;c.bsz=pb.size();
        for(int k=0;k<c.bsz;++k)c.boundary[k]=pb[k];
        c.internalized=(std::find(pb.begin(),pb.end(),shared)==pb.end()?shared:-1);
        c.depth=1+std::max(clusters[A].depth,clusters[B].depth);
        if(c.bsz>2)throw std::runtime_error("boundary >2");
        for(int ps=0;ps<(1<<c.bsz);++ps){
            Envelope best;
            int xlo=0,xhi=1;
            if(c.internalized<0){int x=state_bit(c,ps,shared);xlo=xhi=x;}
            for(int x=xlo;x<=xhi;++x){
                int s1=make_state_for_child(clusters[A],c,ps,shared,x);
                int s2=make_state_for_child(clusters[B],c,ps,shared,x);
                Envelope cand=env_sum(clusters[A].f[s1],clusters[B].f[s2],ct);
                if(c.internalized>=0&&x) cand=env_shift(cand,ex.p[shared],ex.w[shared],ct);
                best=env_max(best,cand,ct);
            }
            c.f[ps]=std::move(best);
        }
        clusters.push_back(std::move(c));ct.joins++;if(clusters.back().internalized>=0)ct.internalizations++;
        ct.max_cluster_depth=std::max<std::uint64_t>(ct.max_cluster_depth,clusters.back().depth);
        return clusters.size()-1;
    }
    int add_internalize(int A,int v,const std::vector<int>&pb){
        Cluster c;c.type=Cluster::INTERNALIZE;c.child1=A;c.internalized=v;c.bsz=pb.size();
        for(int k=0;k<c.bsz;++k)c.boundary[k]=pb[k];
        c.depth=1+clusters[A].depth;if(c.bsz>2)throw std::runtime_error("boundary >2 unary");
        for(int ps=0;ps<(1<<c.bsz);++ps){
            Envelope best;
            for(int x=0;x<=1;++x){
                int cs=make_state_for_child(clusters[A],c,ps,v,x);
                Envelope cand=clusters[A].f[cs];if(x)cand=env_shift(cand,ex.p[v],ex.w[v],ct);
                best=env_max(best,cand,ct);
            }
            c.f[ps]=std::move(best);
        }
        clusters.push_back(std::move(c));ct.internalizations++;ct.max_cluster_depth=std::max<std::uint64_t>(ct.max_cluster_depth,clusters.back().depth);return clusters.size()-1;
    }

    struct AEdge{int a,b,cluster;bool alive=true;};
    void build_component(const std::vector<int>&verts,const std::vector<int>&eids){
        int N=ex.n;
        std::vector<char> aliveV(N,false);for(int v:verts)aliveV[v]=true;
        std::vector<AEdge> ae;ae.reserve(eids.size()*2);
        std::vector<std::vector<int>> inc(N);
        for(int eid:eids){const auto&e=ex.edges[eid];int id=ae.size();ae.push_back({e.a,e.b,add_leaf(eid),true});inc[e.a].push_back(id);inc[e.b].push_back(id);}
        std::vector<int> point(N,-1);
        int aliveCount=verts.size();
        auto other=[&](int eid,int v){return ae[eid].a==v?ae[eid].b:ae[eid].a;};
        auto live_inc=[&](int v){std::vector<int> r;for(int e:inc[v])if(ae[e].alive)r.push_back(e);return r;};
        while(aliveCount>1){
            ct.rounds++;
            std::vector<int> degree(N,0);
            for(const auto&e:ae)if(e.alive){degree[e.a]++;degree[e.b]++;}
            std::vector<int> leaves;
            for(int v:verts)if(aliveV[v]&&degree[v]==1)leaves.push_back(v);
            if(aliveCount==2&&leaves.size()==2) leaves.resize(1);
            struct Rake{int u,v,e;};std::vector<Rake> rs;
            for(int u:leaves){auto li=live_inc(u);if(li.size()!=1)throw std::runtime_error("bad leaf");int e=li[0];rs.push_back({u,other(e,u),e});}
            // Create detached clusters first, then attach to surviving points.
            std::vector<std::pair<int,int>> attachments;
            for(auto r:rs){
                int base=ae[r.e].cluster;int q;
                if(point[r.u]>=0) q=add_join(point[r.u],base,r.u,{r.v});
                else q=add_internalize(base,r.u,{r.v});
                attachments.push_back({r.v,q});ae[r.e].alive=false;aliveV[r.u]=false;aliveCount--;
            }
            for(auto [v,q]:attachments){
                if(!aliveV[v]) throw std::runtime_error("rake survivor removed");
                if(point[v]<0)point[v]=q;else point[v]=add_join(point[v],q,v,{v});
            }
            if(aliveCount<=1)break;
            degree.assign(N,0);for(const auto&e:ae)if(e.alive){degree[e.a]++;degree[e.b]++;}
            std::vector<char> selected(N,false);
            // greedy maximal independent set on degree-2 vertices
            for(int v:verts)if(aliveV[v]&&degree[v]==2){
                bool blocked=false;for(int e:inc[v])if(ae[e].alive){int u=other(e,v);if(selected[u])blocked=true;}
                if(!blocked)selected[v]=true;
            }
            struct Comp{int v,u,w,e1,e2;};std::vector<Comp> cs;
            for(int v:verts)if(selected[v]){
                auto li=live_inc(v);if(li.size()!=2)throw std::runtime_error("bad compress degree");
                int u=other(li[0],v),w=other(li[1],v);cs.push_back({v,u,w,li[0],li[1]});
            }
            if(rs.empty()&&cs.empty()) throw std::runtime_error("contraction stalled");
            for(auto z:cs){
                if(!ae[z.e1].alive||!ae[z.e2].alive)throw std::runtime_error("compress edge conflict");
                int c1=ae[z.e1].cluster,c2=ae[z.e2].cluster;
                if(point[z.v]>=0)c1=add_join(point[z.v],c1,z.v,sorted_boundary({z.u,z.v}));
                int nc=add_join(c1,c2,z.v,sorted_boundary({z.u,z.w}));
                ae[z.e1].alive=false;ae[z.e2].alive=false;aliveV[z.v]=false;aliveCount--;
                int ne=ae.size();ae.push_back({z.u,z.w,nc,true});inc[z.u].push_back(ne);inc[z.w].push_back(ne);
            }
        }
        int rootv=-1;for(int v:verts)if(aliveV[v]){rootv=v;break;}
        if(rootv<0||point[rootv]<0)throw std::runtime_error("missing final point cluster");
        int root=add_internalize(point[rootv],rootv,{});roots.push_back(root);
    }
    void build_components_and_hierarchy(){
        std::vector<std::vector<std::pair<int,int>>> adj(ex.n);
        for(int e=0;e<(int)ex.edges.size();++e){adj[ex.edges[e].a].push_back({ex.edges[e].b,e});adj[ex.edges[e].b].push_back({ex.edges[e].a,e});}
        std::vector<char> seen(ex.n,false);
        for(int s=0;s<ex.n;++s)if(!seen[s]){
            std::vector<int> vs,es,stack={s};seen[s]=true;
            while(!stack.empty()){int v=stack.back();stack.pop_back();vs.push_back(v);for(auto [u,e]:adj[v]){es.push_back(e);if(!seen[u]){seen[u]=true;stack.push_back(u);}}}
            std::sort(es.begin(),es.end());es.erase(std::unique(es.begin(),es.end()),es.end());
            if(es.empty())throw std::runtime_error("expanded isolated unexpected");
            build_component(vs,es);
        }
    }

    struct ActivePtrs { std::array<size_t,4> idx{}; };
    Line active_line(const Cluster&c,int st,const ActivePtrs&ap)const{
        if (!c.f[st].feasible) throw std::runtime_error("active infeasible");
        return c.f[st].lines[ap.idx[st]];
    }
    bool selected_at_rat(const Cluster&node,const std::vector<ActivePtrs>&aps,const Rat&q,const std::array<int,2>&pvals) {
        auto get_branch=[&](int x,bool&feas)->Line{
            Line sum{0,0};feas=true;int kids[2]={node.child1,node.child2};int nk=node.child2>=0?2:1;
            for(int z=0;z<nk;++z){int cid=kids[z];const Cluster&ch=clusters[cid];int st=0;for(int k=0;k<ch.bsz;++k){int v=ch.boundary[k],val;if(v==node.internalized)val=x;else{int pos=-1;for(int j=0;j<node.bsz;++j)if(node.boundary[j]==v)pos=j;if(pos<0)throw std::runtime_error("mapping threshold event");val=pvals[pos];}st|=val<<k;}if(!ch.f[st].feasible){feas=false;return{};}Line l=active_line(ch,st,aps[z]);sum.P+=l.P;sum.W+=l.W;}
            if(x){sum.P+=ex.p[node.internalized];sum.W+=ex.w[node.internalized];}return sum;
        };
        bool f0,f1;Line l0=get_branch(0,f0),l1=get_branch(1,f1);if(!f1)return false;if(!f0)return true;
        i128 v0=(i128)l0.P*q.den-(i128)q.num*l0.W; i128 v1=(i128)l1.P*q.den-(i128)q.num*l1.W;return v1>=v0;
    }

    Rat recover_internalized(const Cluster&node){
        if(node.internalized<0)throw std::runtime_error("not internalized");
        int kids[2]={node.child1,node.child2};int nk=node.child2>=0?2:1;
        std::vector<std::vector<Rat>> lists;
        for(int z=0;z<nk;++z){const Cluster&ch=clusters[kids[z]];for(int st=0;st<(1<<ch.bsz);++st)if(ch.f[st].feasible)lists.push_back(envelope_breakpoints(ch.f[st],ct));}
        for(int k=0;k<node.bsz;++k){int v=node.boundary[k];if(!theta_known[v])throw std::runtime_error("parent boundary threshold unknown");lists.push_back({theta_exp[v]});}
        auto events=merge_events_linear(lists,ct);ct.topdown_events+=events.size();
        std::vector<ActivePtrs> aps(nk);
        std::array<int,2> pvals{1,1}; // at -infinity all selected
        auto branch_lines=[&](int x,bool&f0)->Line{
            Line sum{0,0};f0=true;
            for(int z=0;z<nk;++z){const Cluster&ch=clusters[kids[z]];int st=0;for(int k=0;k<ch.bsz;++k){int v=ch.boundary[k],val;if(v==node.internalized)val=x;else{int pos=-1;for(int j=0;j<node.bsz;++j)if(node.boundary[j]==v)pos=j;if(pos<0)throw std::runtime_error("map open interval");val=pvals[pos];}st|=val<<k;}if(!ch.f[st].feasible){f0=false;return{};}Line l=active_line(ch,st,aps[z]);sum.P+=l.P;sum.W+=l.W;}
            if(x){sum.P+=ex.p[node.internalized];sum.W+=ex.w[node.internalized];}return sum;
        };
        auto root_in_interval=[&](bool haslo,const Rat&lo,bool hashi,const Rat&hi,bool selected_lo,Rat&ans)->int{
            bool f0,f1;Line l0=branch_lines(0,f0),l1=branch_lines(1,f1);ct.topdown_scans++;
            if(!f1){if(haslo&&selected_lo){ans=lo;return 1;}return -1;}
            if(!f0)return 0;
            i64 A=l1.P-l0.P, B=l1.W-l0.W;
            if(B<0) throw std::runtime_error("branch advantage increases");
            if(B==0){if(A<0){if(haslo&&selected_lo){ans=lo;return 1;}return -1;}return 0;}
            Rat r=make_rat(A,B);
            bool gtlo=!haslo||cmp_rat(r,lo)>0;bool lthi=!hashi||cmp_rat(r,hi)<0;
            if(gtlo&&lthi){ans=r;return 1;}
            if(haslo&&cmp_rat(r,lo)<=0){if(selected_lo){ans=lo;return 1;}return -1;}
            return 0;
        };
        bool haslo=false;Rat lo;bool selected_lo=true;
        for(const Rat&q:events){
            Rat ans;int got=root_in_interval(haslo,lo,true,q,selected_lo,ans);if(got==1)return ans;if(got<0)throw std::runtime_error("threshold before interval");
            bool atq=selected_at_rat(node,aps,q,pvals);
            // advance envelope pointers at q
            for(int z=0;z<nk;++z){const Cluster&ch=clusters[kids[z]];for(int st=0;st<(1<<ch.bsz);++st){if(!ch.f[st].feasible)continue;auto &idx=aps[z].idx[st];while(idx+1<ch.f[st].lines.size()&&rat_eq(next_bp(ch.f[st],idx,&ct),q))++idx;}}
            // parent threshold tie is selected at q, then switches to 0 to the right
            for(int k=0;k<node.bsz;++k)if(rat_eq(theta_exp[node.boundary[k]],q))pvals[k]=0;
            lo=q;haslo=true;selected_lo=atq;
        }
        Rat ans;int got=root_in_interval(haslo,lo,false,Rat{},selected_lo,ans);if(got==1)return ans;
        throw std::runtime_error("no finite threshold found");
    }
    void recover(int id){
        Cluster&c=clusters[id];
        if(c.internalized>=0){Rat th=recover_internalized(c);int v=c.internalized;if(theta_known[v]&&!rat_eq(theta_exp[v],th))throw std::runtime_error("inconsistent duplicate threshold");theta_exp[v]=th;theta_known[v]=true;}
        if(c.type==Cluster::LEAF)return;
        if (c.child1 >= 0) recover(c.child1);
        if (c.child2 >= 0) recover(c.child2);
    }
};



}  // namespace

MacroitemSequence compute_rac(const Instance& instance, RaCStats* stats) {
    validate_instance(instance);
    IntInstance in;
    in.n = instance.n;
    in.p = instance.profit;
    in.w = instance.weight;
    in.arcs.reserve(instance.arcs.size());
    for (const Arc& arc : instance.arcs) in.arcs.push_back({arc.tail, arc.head});

    RaCSolver solver(in);
    const IntSequence seq = solver.solve();
    MacroitemSequence out;
    out.macroitems.reserve(seq.macroitems.size());
    for (const auto& im : seq.macroitems) {
        Macroitem m;
        m.nodes = im.nodes;
        m.profit = im.p;
        m.weight = im.w;
        out.macroitems.push_back(std::move(m));
    }
    if (stats) *stats = solver.counters();
    return out;
}

}  // namespace pcf
