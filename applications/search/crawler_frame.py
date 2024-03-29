import logging
from datamodel.search.datamodel import ProducedLink, OneUnProcessedGroup, robot_manager
from spacetime_local.IApplication import IApplication
from spacetime_local.declarations import Producer, GetterSetter, Getter
#from lxml import html,etree
import re, os
from time import time
from bs4 import BeautifulSoup
from urlparse import urljoin

try:
    # For python 2
    from urlparse import urlparse, parse_qs
except ImportError:
    # For python 3
    from urllib.parse import urlparse, parse_qs


logger = logging.getLogger(__name__)
LOG_HEADER = "[CRAWLER]"
url_count = (set()
    if not os.path.exists("successful_urls.txt") else
    set([line.strip() for line in open("successful_urls.txt").readlines() if line.strip() != ""]))
MAX_LINKS_TO_DOWNLOAD = 3000

if not os.path.exists("analytics.txt"):
    invalid_links = 0
    most_out_links = 0
    big_page = "none"
    avg_download = 0
    runtime = 0

else:
    with open("analytics.txt", "r") as f:
        line = f.readline()

        try:
            invalid_links = int(line.split()[0])
            most_out_links = int(line.split()[1])
            big_page = line.split()[2]
            avg_download = float(line.split()[3])
            runtime = float(line.split()[4])
        except:
            invalid_links = 0
            most_out_links = 0
            big_page = "none"
            avg_download = 0
            runtime = 0
        # if line.strip() == "":
        #     invalid_links = 0
        #     most_out_links = 0
        #     big_page = "none"
        #     avg_download = 0
        #     runtime = 0
        # else:
        #     invalid_links = int(line.split()[0])
        #     most_out_links = int(line.split()[1])
        #     big_page = line.split()[2]
        #     avg_download = float(line.split()[3])
        #     runtime = float(line.split()[4])

@Producer(ProducedLink)
@GetterSetter(OneUnProcessedGroup)
class CrawlerFrame(IApplication):

    def __init__(self, frame):
        self.starttime = time()
        # Set app_id <student_id1>_<student_id2>...
        self.app_id = "34216498_32075491"
        # Set user agent string to IR W17 UnderGrad <student_id1>, <student_id2> ...
        # If Graduate studetn, change the UnderGrad part to Grad.
        self.UserAgentString = "IR W17 Undergrad 34216498, 32075491"

        self.frame = frame
        assert(self.UserAgentString != None)
        assert(self.app_id != "")
        if len(url_count) >= MAX_LINKS_TO_DOWNLOAD:
            self.done = True

    def initialize(self):
        self.count = 0
        l = ProducedLink("http://www.ics.uci.edu", self.UserAgentString)
        print l.full_url
        self.frame.add(l)

    def update(self):
        for g in self.frame.get(OneUnProcessedGroup):
            print "Got a Group"
            outputLinks, urlResps = process_url_group(g, self.UserAgentString)
            for urlResp in urlResps:
                if urlResp.bad_url and self.UserAgentString not in set(urlResp.dataframe_obj.bad_url):
                    urlResp.dataframe_obj.bad_url += [self.UserAgentString]
            for l in outputLinks:
                if is_valid(l) and robot_manager.Allowed(l, self.UserAgentString):
                    lObj = ProducedLink(l, self.UserAgentString)
                    self.frame.add(lObj)
        if len(url_count) >= MAX_LINKS_TO_DOWNLOAD:
            self.done = True

    def shutdown(self):
        global avg_download
        global runtime
        runtime += time() - self.starttime
        avg_download = runtime / len(url_count)


        print "downloaded", len(url_count), "in", time() - self.starttime, "seconds."
        print "Number of invalid links:", invalid_links
        print "Page with the most output links (",most_out_links,"):", big_page
        print "Average download time per page:", avg_download
        save_analytics()
        pass

def save_count(urls):
    global url_count
    urls = set(urls).difference(url_count)
    url_count.update(urls)
    if len(urls):
        with open("successful_urls.txt", "a") as surls:
            surls.write(("\n".join(urls) + "\n").encode("utf-8"))

def save_analytics():
    global invalid_links
    global most_out_links
    global big_page
    global avg_download
    global runtime

    txt = open("analytics.txt", "w")
    txt.write(str(invalid_links) + " " + str(most_out_links) + " " + big_page + " " + str(avg_download) + " " + str(runtime))
    txt.close()

def process_url_group(group, useragentstr):
    rawDatas, successfull_urls = group.download(useragentstr, is_valid)
    save_count(successfull_urls)
    return extract_next_links(rawDatas), rawDatas

#######################################################################################
'''
STUB FUNCTIONS TO BE FILLED OUT BY THE STUDENT.
'''
def extract_next_links(rawDatas):
    outputLinks = list()
    '''
    rawDatas is a list of objs -> [raw_content_obj1, raw_content_obj2, ....]
    Each obj is of type UrlResponse  declared at L28-42 datamodel/search/datamodel.py
    the return of this function should be a list of urls in their absolute form
    Validation of link via is_valid function is done later (see line 42).
    It is not required to remove duplicates that have already been downloaded.
    The frontier takes care of that.

    Suggested library: lxml
    '''

    global most_out_links
    global big_page
    for response in rawDatas:
        if response.http_code >= 400:         #ignore crawling websites with error code
            continue
        soup = BeautifulSoup(response.content, 'lxml')

        specificSoup = soup.find_all('a', href=True)
        for link in specificSoup:
            absUrl = urljoin(response.url, link['href'])
            #print absUrl
            #print
            outputLinks.append(absUrl)

            # print link['href']
            # print absUrl
            # print
            # print
        if len(specificSoup) >= most_out_links:
            most_out_links = len(specificSoup)
            big_page = response.url
        print len(specificSoup)

    print len(rawDatas)
    print "------------------------              " + str(len(outputLinks))
    print


    return outputLinks

def is_valid(url):
    '''
    Function returns True or False based on whether the url has to be downloaded or not.
    Robot rules and duplication rules are checked separately.

    This is a great place to filter out crawler traps.
    '''
    parsed = urlparse(url)
    global invalid_links
    #
    # print "@@@@@@@@@@@@@@"
    # print parsed.hostname
    # print parsed.path
    # print "@@@@@@@@@@@@@@"
    #
    if parsed.hostname == None:
        return False
    if "calendar.ics.uci.edu" in parsed.hostname:
        return False
    if "ganglia.ics.uci.edu" in parsed.hostname:
        return False
    if "/~mlearn/" in parsed.path:
        return False
    if "graphmod" in parsed.hostname:
        return False
    if ".php/" in parsed.path:
        return False
    if "grad/resources" in parsed.path:
        return False
    if "http:" in parsed.path:
        return False
    if "https:" in parsed.path:
        return False
    if "gd?C=M;O=D" in parsed.path:
        return False



    if parsed.scheme not in set(["http", "https"]):
        invalid_links += 1
        return False
    try:
        result =  ".ics.uci.edu" in parsed.hostname \
            and not re.match(".*\.(css|js|bmp|gif|jpe?g|ico" + "|png|tiff?|mid|mp2|mp3|mp4"\
            + "|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf" \
            + "|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1" \
            + "|thmx|mso|arff|rtf|jar|csv"\
            + "|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()) \

        if not result:
            invalid_links += 1
        return result

    except TypeError:
        print ("TypeError for ", parsed)
